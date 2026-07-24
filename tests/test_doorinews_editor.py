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
        text = "#비트코인은 #미국에서 #시장구조법안이 통과됨"
        self.assertEqual(
            editor.fix_hashtag_particles(text),
            "#비트코인 은 #미국 에서 #시장구조법안 이 통과됨",
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


if __name__ == "__main__":
    unittest.main()
