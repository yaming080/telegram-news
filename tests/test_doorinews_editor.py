import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import doorinews_editor as editor


class DoorinewsEditorTests(unittest.TestCase):
    def test_asset_only_signatures_are_not_duplicates(self):
        one = {"title": "Bitcoin and XRP market update", "desc": "BTC XRP crypto market"}
        two = {"title": "XRP and Bitcoin trading recap", "desc": "XRP BTC crypto market"}
        self.assertEqual(editor.build_story_signature(one), "")
        self.assertFalse(
            editor.is_semantically_duplicate(
                two,
                [editor.build_story_signature(one)],
                [one["title"]],
            )
        )

    def test_cross_source_same_event_is_duplicate(self):
        first = {
            "title": "SBI and Rakuten develop crypto investment trusts in Japan",
            "desc": "Japan approved rules allowing securities firms to launch Bitcoin investment trusts",
        }
        second = {
            "title": "Japanese brokers prepare Bitcoin trust products after regulatory approval",
            "desc": "Rakuten and SBI are developing investment trust products under Japan's new rules",
        }
        first_sig = editor.build_story_signature(first)
        second_sig = editor.build_story_signature(second)
        self.assertTrue(first_sig)
        self.assertTrue(second_sig)
        self.assertTrue(editor._same_event(first_sig, second_sig))

    def test_different_events_for_same_assets_are_not_duplicates(self):
        first = {
            "title": "Morgan Stanley files Ethereum ETF application",
            "desc": "The bank filed an ETF application with the SEC in the United States",
        }
        second = {
            "title": "Aave restores WETH collateral ratios after rsETH recovery",
            "desc": "Aave restored lending functions on Ethereum",
        }
        self.assertFalse(
            editor._same_event(
                editor.build_story_signature(first),
                editor.build_story_signature(second),
            )
        )

    def test_particles_are_separated(self):
        text = "#비트코인은 #미국에서 #클래리티법안이 통과됨"
        self.assertEqual(
            editor.fix_hashtag_particles(text),
            "#비트코인 은 #미국 에서 #클래리티법안 이 통과됨",
        )

    def test_x_is_not_translated_and_milestone_is_not_ton(self):
        cleaned = editor._clean_summary(
            "로빈후드 CEO의 엑스 계정에 밈코인 게시물이 등장함\n\n"
            "지갑 수가 마일스톤을 달성함"
        )
        self.assertIn("X 계정", cleaned)
        self.assertIn("마일스톤", cleaned)
        self.assertNotIn("#톤", cleaned)

    def test_summary_is_not_cut_mid_sentence(self):
        text = (
            "모건스탠리가 이더리움 현물 ETF 수정 신고서를 제출함\n\n"
            "뉴욕증권거래소 상장 승인 절차를 추진함\n\n"
            "불필요한 세 번째 배경 설명임"
        )
        result = editor.format_summary_for_telegram(text, max_sentences=2, max_chars=20)
        self.assertEqual(
            result,
            "모건스탠리가 이더리움 현물 ETF 수정 신고서를 제출함\n\n"
            "뉴욕증권거래소 상장 승인 절차를 추진함",
        )

    def test_price_prediction_is_blocked(self):
        story = {
            "title": "XRP price prediction: Will XRP reach $10?",
            "desc": "An analyst discusses support and resistance levels",
        }
        blocked, _ = editor._is_hard_blocked(story)
        self.assertTrue(blocked)

    def test_concrete_crypto_event_is_allowed(self):
        story = {
            "title": "BC Card secures stablecoin payment patent",
            "desc": "The company announced blockchain payment infrastructure in Korea",
        }
        blocked, _ = editor._is_hard_blocked(story)
        self.assertFalse(blocked)

    def test_market_recovery_narrative_is_blocked(self):
        story = {
            "title": "Bitcoin Recovery Strengthens as Supply Returns to Profit: Is the Bear Market Over?",
            "desc": "BTC holders are back in profit as resistance remains important",
        }
        blocked, _ = editor._is_hard_blocked(story)
        self.assertTrue(blocked)

    def test_metric_only_story_has_no_positive_event(self):
        story = {
            "title": "XRP Has Welcomed $800M Worth of Distributed RWA in 2026",
            "desc": "The report measures assets on XRP Ledger",
        }
        self.assertFalse(editor._matches(editor._story_text(story), editor.CONCRETE_EVENT_PATTERNS))

    def test_commentary_and_project_migration_are_blocked(self):
        stories = (
            {
                "title": "Crypto Biz: Is the AI-to-crypto rotation underway?",
                "desc": "Bitcoin and AI market commentary",
            },
            {
                "title": "A quantum roadmap would push Bitcoin much higher",
                "desc": "A commentator discusses a possible BTC future",
            },
            {
                "title": "Augur issues final call for mandatory REP migration",
                "desc": "The historic fork nears completion on Ethereum",
            },
            {
                "title": "World Foundation raises $52.5M through WLD token sale",
                "desc": "The funding will expand World ID blockchain infrastructure",
            },
        )
        for story in stories:
            with self.subTest(title=story["title"]):
                blocked, _ = editor._is_hard_blocked(story)
                self.assertTrue(blocked)

    def test_gold_and_silver_need_english_metal_context(self):
        korean_particle = "금은 일반 문장에서 태그가 아님"
        metal_story = "Bitcoin outperformed Gold and Silver this year"
        self.assertFalse(editor._has_precious_metal_context(korean_particle, "gold"))
        self.assertFalse(editor._has_precious_metal_context(korean_particle, "silver"))
        self.assertTrue(editor._has_precious_metal_context(metal_story, "gold"))
        self.assertTrue(editor._has_precious_metal_context(metal_story, "silver"))

    def test_target_inline_tags_and_footer(self):
        story = {
            "title": "EU sanctions package includes Justin Sun's HTX over Russia services",
            "desc": "Tether says the freeze does not amount to an exchange-wide asset freeze",
        }
        summary = (
            "유럽연합, 러시아 제재 패키지에 저스틴선 의 HTX 포함\n\n"
            "테더는 거래소 전체 자산 동결 수준은 아니라고 설명함"
        )
        tagged, selected = editor._inject_inline_tags(summary, story)
        self.assertIn("#유럽연합", tagged)
        self.assertIn("#러시아", tagged)
        self.assertIn("#저스틴선 의", tagged)
        self.assertIn("#HTX", tagged)
        footer = editor._build_footer_tags(story, selected)
        self.assertIn("#JustinSun", footer)
        self.assertIn("#HTX", footer)
        self.assertNotIn("#Russia", footer)
        for fixed in editor.FIXED_FOOTER_TAGS:
            self.assertIn(fixed, footer)

    def test_bhutan_denial_is_cross_source_duplicate(self):
        first = {
            "title": "Bhutan denies selling Bitcoin after $1 billion wallet outflow report",
            "desc": "Bhutan disputed claims that it sold BTC from state-linked wallets",
        }
        second = {
            "title": "Bhutan does not recall any Bitcoin sale amid $1 billion drawdown claim",
            "desc": "The country denied a widely tracked BTC disposal report",
        }
        self.assertTrue(
            editor._same_event(
                editor.build_story_signature(first),
                editor.build_story_signature(second),
            )
        )

    def test_bc_card_patent_is_cross_source_duplicate(self):
        first = {
            "title": "BC Card secures stablecoin payment infrastructure patent in Korea",
            "desc": "The blockchain payment patent covers domestic and cross-border settlement",
        }
        second = {
            "title": "Korean card company obtains blockchain patent for stablecoin payments",
            "desc": "BC Card secured intellectual property for digital asset payment infrastructure",
        }
        self.assertTrue(
            editor._same_event(
                editor.build_story_signature(first),
                editor.build_story_signature(second),
            )
        )

    def test_eu_russia_sanctions_are_cross_source_duplicate(self):
        first = {
            "title": "EU extends crypto transaction bans in latest Russia sanctions package",
            "desc": "The European Union sanctioned platforms linked to Russia",
        }
        second = {
            "title": "European Union strikes Russia war economy with new crypto bans",
            "desc": "The EU expanded banking and crypto sanctions against Russia",
        }
        self.assertTrue(
            editor._same_event(
                editor.build_story_signature(first),
                editor.build_story_signature(second),
            )
        )

    def test_kazakhstan_miner_electricity_fee_is_blocked(self):
        story = {
            "title": "Kazakhstan rolls out capped electricity fees for crypto miners",
            "desc": "Bitcoin mining companies can apply for a power tariff cap",
        }
        blocked, reason = editor._is_hard_blocked(story)
        self.assertTrue(blocked)
        self.assertTrue(reason)

    def test_clarity_support_without_procedural_progress_is_blocked(self):
        story = {
            "title": "Goldman Sachs CEO backs CLARITY Act",
            "desc": "The executive urged Congress to support the crypto market structure bill",
        }
        blocked, reason = editor._is_hard_blocked(story)
        self.assertTrue(blocked)
        self.assertIn("클래리티법안", reason)

    def test_clarity_committee_passage_is_allowed(self):
        story = {
            "title": "CLARITY Act passes Senate committee vote",
            "desc": "The crypto market structure bill advanced after a scheduled committee vote",
        }
        blocked, _ = editor._is_hard_blocked(story)
        self.assertFalse(blocked)

    def test_first_ripple_mention_only_is_tagged(self):
        story = {
            "title": "Ripple launches institutional RLUSD platform",
            "desc": "Ripple added monitoring and API management for institutions",
        }
        summary = (
            "리플이 기관용 RLUSD 플랫폼을 출시함\n\n"
            "RLUSD 관리 기능을 통해 #리플 서비스 접근성을 강화함"
        )
        tagged, _ = editor._inject_inline_tags(summary, story)
        self.assertTrue(tagged.startswith("#리플 이 기관용"))
        self.assertEqual(tagged.count("#리플"), 1)
        self.assertIn("통해 리플 서비스", tagged)

    def test_key_people_use_korean_name_tags_before_titles(self):
        story = {
            "title": "Kristin Smith and Goldman Sachs CEO David Solomon discuss CLARITY Act",
            "desc": "Both voiced support for the crypto market structure bill",
        }
        summary = (
            "크리스틴 스미스는 법안 처리 필요성을 설명함\n\n"
            "골드만삭스 CEO 데이비드 솔로몬이 CLARITY 지지를 공개함"
        )
        tagged, _ = editor._inject_inline_tags(summary, story)
        self.assertIn("#크리스틴스미스 는", tagged)
        self.assertIn("#데이비드솔로몬 이", tagged)
        self.assertNotIn("#CEO", tagged)

    def test_clarity_is_korean_in_body_and_footer(self):
        story = {
            "title": "CLARITY Act passes committee vote",
            "desc": "The market structure bill advanced in Congress",
        }
        summary = "CLARITY 통과로 미국의 암호화폐 규제 절차가 진전됨"
        tagged, selected = editor._inject_inline_tags(summary, story)
        self.assertEqual(tagged.count("#클래리티법안"), 1)
        self.assertIn("#클래리티법안 통과", tagged)
        self.assertNotRegex(tagged, r"(?i)clarity")

        footer = editor._build_footer_tags(story, selected)
        self.assertIn("#클래리티법안", footer)
        self.assertNotIn("#ClarityAct", footer)
        self.assertNotIn("#CLARITY", footer)
        self.assertNotIn("#Act", footer)

    def test_strategy_company_is_tagged_at_first_mention(self):
        story = {
            "title": "Strategy STRC added to three major US preferred stock ETFs",
            "desc": "The ETFs hold a combined 7.56 million dollars of STRC",
        }
        summary = (
            "스트래티지의 STRC가 미국 우선주 ETF 3곳의 편입 종목에 오르며 "
            "월간 자금 유입이 확대됐다고 밝힘"
        )
        tagged, _ = editor._inject_inline_tags(summary, story)
        self.assertTrue(tagged.startswith("#스트래티지 의"))
        self.assertEqual(tagged.count("#스트래티지"), 1)

    def test_franklin_templeton_and_etf_particle_are_tagged(self):
        story = {
            "title": "Franklin Templeton XRP ETF reports quarterly holdings",
            "desc": "A US asset manager disclosed shares of the Franklin Templeton XRP ETF",
        }
        summary = (
            "미국 자산운용사가 프랭클린 템플턴의 XRP ETF인 상품 보유 내역을 공개함"
        )
        tagged, _ = editor._inject_inline_tags(summary, story)
        self.assertIn("#프랭클린템플턴 의", tagged)
        self.assertIn("#ETF 인", tagged)
        self.assertEqual(tagged.count("#프랭클린템플턴"), 1)

    def test_known_companies_use_korean_inline_tags(self):
        story = {
            "title": "BlackRock and Robinhood launch a crypto partnership",
            "desc": "The two companies announced the service",
        }
        summary = "블랙록이 로빈후드와 암호화폐 서비스를 출시함"
        tagged, _ = editor._inject_inline_tags(summary, story)
        self.assertIn("#블랙록 이", tagged)
        self.assertIn("#로빈후드 와", tagged)


if __name__ == "__main__":
    unittest.main()
