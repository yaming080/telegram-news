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

    def test_complete_country_tag_is_not_split_as_particle(self):
        text = "#인도 집행국이 #ETF인 상품을 조사함"
        self.assertEqual(
            editor.fix_hashtag_particles(text),
            "#인도 집행국이 #ETF 인 상품을 조사함",
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

    def test_concrete_target_asset_event_is_allowed(self):
        story = {
            "title": "BC Card secures Bitcoin payment patent",
            "desc": "The company announced BTC payment infrastructure in Korea",
        }
        blocked, _ = editor._is_hard_blocked(story)
        self.assertFalse(blocked)

    def test_concrete_non_target_asset_event_is_blocked(self):
        story = {
            "title": "BC Card secures stablecoin payment patent",
            "desc": "The company announced blockchain payment infrastructure in Korea",
        }
        blocked, reason = editor._is_hard_blocked(story)
        self.assertTrue(blocked)
        self.assertIn("지정 코인", reason)

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
        self.assertNotIn("#JustinSun", footer)
        self.assertNotIn("#HTX", footer)
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

    def test_generic_clarity_committee_passage_without_target_asset_is_blocked(self):
        story = {
            "title": "CLARITY Act passes Senate committee vote",
            "desc": "The crypto market structure bill advanced after a scheduled committee vote",
        }
        blocked, reason = editor._is_hard_blocked(story)
        self.assertTrue(blocked)
        self.assertIn("지정 코인", reason)

    def test_clarity_vote_seeking_before_recess_is_blocked(self):
        story = {
            "title": "Crypto groups seek Senate votes for CLARITY Act before August recess",
            "desc": "Industry groups urged lawmakers to change the bill before recess",
        }
        blocked, reason = editor._is_hard_blocked(story)
        self.assertTrue(blocked)
        self.assertIn("클래리티법안", reason)

    def test_bitmex_shutdown_variants_are_same_event(self):
        insurance_story = {
            "title": "BitMEX faces questions over insurance fund before September 23 shutdown",
            "desc": (
                "The crypto exchange will close on September 23, 2026 while plaintiffs "
                "prepare a class action over customer losses"
            ),
        }
        withdrawal_story = {
            "title": "BitMEX to permanently close trading platform on September 23, 2026",
            "desc": "Users were urged to close open positions and withdraw remaining funds",
        }
        first = editor.build_story_signature(insurance_story)
        second = editor.build_story_signature(withdrawal_story)
        self.assertIn("action_close", first)
        self.assertIn("object_platform", second)
        self.assertIn("date_2026_09_23", first)
        self.assertTrue(editor._same_event(first, second))

    def test_bitmex_shutdown_matches_historical_title_signature(self):
        story = {
            "title": "BitMEX customers allege unfair liquidation in class action",
            "desc": (
                "BitMEX disclosed a September 23, 2026 shutdown and customers claim "
                "622.66 BTC in losses"
            ),
        }
        seen_title = "BitMEX to shut down exchange platform on September 23, 2026"
        self.assertTrue(editor.is_semantically_duplicate(story, [], [seen_title]))

    def test_summary_spacing_for_india_hawala_story(self):
        cleaned = editor._clean_summary(
            "#인도 집행국이 암호화폐 하왈라자금세탁망을 적발함\n\n"
            "은행계좌와 페이퍼컴퍼니를 확인했다고 설명함"
        )
        self.assertIn("하왈라 자금 세탁망", cleaned)
        self.assertIn("은행 계좌", cleaned)
        self.assertIn("페이퍼 컴퍼니", cleaned)

    def test_source_domain_does_not_create_crypto_context(self):
        story = {
            "title": "Nvidia, Microsoft, Meta and IBM disclose AI training data",
            "desc": "Technology companies answered a US congressional inquiry about AI models",
            "url": "https://crypto.news/nvidia-microsoft-ai-training-data/",
        }
        blocked, reason = editor._is_hard_blocked(story)
        self.assertTrue(blocked)
        self.assertIn("지정 코인 핵심맥락 없음", reason)

    def test_aggregate_web3_scam_report_is_blocked(self):
        story = {
            "title": "OKX H1 2026 Web3 security report reveals phishing losses",
            "desc": "The report counted 182 incidents and $94.56 million in scam losses",
        }
        blocked, reason = editor._is_hard_blocked(story)
        self.assertTrue(blocked)
        self.assertIn("보안", reason)

    def test_strategy_preferred_stock_rebound_is_blocked(self):
        story = {
            "title": "Strategy preferred stock SATA rebounds 16% toward par value",
            "desc": "The shares recovered from a June low as investors reassessed the stock",
        }
        blocked, _ = editor._is_hard_blocked(story)
        self.assertTrue(blocked)

    def test_only_operator_selected_assets_are_recognized(self):
        examples = {
            "BTC": "Bitcoin BTC",
            "ETH": "Ethereum ETH",
            "XRP": "Ripple XRP",
            "XLM": "Stellar XLM",
            "BCH": "Bitcoin Cash BCH",
            "ETC": "Ethereum Classic ETC",
            "TRX": "TRON TRX",
            "ADA": "Cardano ADA",
            "BNB": "Binance Coin BNB",
            "SHIB": "Shiba Inu SHIB",
            "FLR": "Flare Network FLR",
            "ENA": "Ethena ENA",
        }
        for symbol, text in examples.items():
            with self.subTest(symbol=symbol):
                self.assertIn(symbol, editor.target_assets(text))
        self.assertFalse(editor.target_assets("BMX token rebounds on BitMart"))
        self.assertFalse(editor.target_assets("Solana SOL launches a new product"))

    def test_bmx_bitmart_story_from_screenshot_is_blocked(self):
        story = {
            "title": "BMX token rebounds after July 24 plunge",
            "desc": "BitMart withdrawal-delay rumors spread through the market",
        }
        self.assertFalse(editor.matches_keywords(story, [], [], []))

    def test_etf_net_flow_and_weekly_close_cards_are_blocked(self):
        stories = (
            {
                "title": "Ethereum ETF ends five-day inflow streak with weekly net outflow",
                "desc": "Bitcoin ETF also recorded its second straight daily net outflow",
            },
            {
                "title": "이더리움 ETF 5거래일 연속 유입 종료, 주간 마감은 순유출",
                "desc": "비트코인 ETF도 이틀째 순유출을 기록함",
            },
        )
        for story in stories:
            with self.subTest(title=story["title"]):
                blocked, reason = editor._is_hard_blocked(story)
                self.assertTrue(blocked)
                self.assertIn("수급", reason)

    def test_korean_story_hashes_do_not_overwrite_each_other(self):
        first = "미국 국무부, 비트코인정책연구소 파트너를 자문역으로 지명"
        second = "리플, 기관용 결제 플랫폼 출시"
        self.assertEqual(editor.story_hash(first), editor.story_hash(first))
        self.assertNotEqual(editor.story_hash(first), editor.story_hash(second))
        self.assertNotEqual(editor.story_hash(first), editor.story_hash(""))

    def test_screenshot_duplicate_event_pairs(self):
        pairs = (
            (
                "poolin_bankruptcy",
                {
                    "title": "Poolin files for Chapter 11 bankruptcy with two US affiliates",
                    "desc": "The Bitcoin mining pool plans an asset auction after filing for protection",
                },
                {
                    "title": "비트코인 채굴풀 풀린, 미국 계열사와 챕터11 파산보호 신청",
                    "desc": "풀린은 채굴 자산 매각과 사업 종료를 추진함",
                },
            ),
            (
                "citadel_investment",
                {
                    "title": "Citadel Securities invests $400 million in crypto derivatives infrastructure",
                    "desc": "The market maker backed an expansion of digital asset products",
                },
                {
                    "title": "시타델 증권, 암호화폐 파생상품 인프라에 4억달러 투자",
                    "desc": "시타델증권은 디지털자산 사업 확대를 추진함",
                },
            ),
            (
                "bitmex_class_action",
                {
                    "title": "BitMEX customers file class action over secret insider trading desk",
                    "desc": "Plaintiffs including former clients claim about 623 BTC in losses",
                },
                {
                    "title": "비트멕스 고객 2명, 내부자 거래 의혹 집단소송 제기",
                    "desc": "원고는 622.66BTC를 잃었다고 주장함",
                },
            ),
            (
                "arbitrum_dev3pack",
                {
                    "title": "Arbitrum publishes final Dev3pack grant report",
                    "desc": "The report records 1,018 developers and nine teams entering the Uniswap incubator",
                },
                {
                    "title": "아비트럼, 보조금 기반 Dev3pack 최종 보고서 공개",
                    "desc": "개발자 1,018명과 9개 팀의 유니스왑 인큐베이터 진입 성과를 밝힘",
                },
            ),
            (
                "tango_shutdown",
                {
                    "title": "DEX Tango to shut down its network on August 13, 2026",
                    "desc": "The derivatives service is ending four months after launch",
                },
                {
                    "title": "파생상품 DEX 탱고, 2026년 8월 13일 네트워크 종료",
                    "desc": "출시 약 4개월 만에 서비스를 종료함",
                },
            ),
            (
                "ripple_rlusd",
                {
                    "title": "Ripple launches RLUSD mint as banks expand adoption",
                    "desc": "Ripple introduced new RLUSD issuance functions",
                },
                {
                    "title": "리플, RLUSD 민트 출시",
                    "desc": "은행 채택 확대에 맞춰 RLUSD 발행 기능을 공개함",
                },
            ),
            (
                "triplea_hot_wallet",
                {
                    "title": "Triple-A hot wallet attack drains $9.7 million",
                    "desc": "The suspected exploit moved 5,226.66 ETH",
                },
                {
                    "title": "트리플A 핫월렛 의심 공격으로 970만달러 유출",
                    "desc": "수신 주소에 약 5,226.66ETH가 모임",
                },
            ),
            (
                "franklin_xrp_etf_holdings",
                {
                    "title": "Ledger Capital discloses 16,745 shares of Franklin Templeton XRP ETF in 2026 Q2",
                    "desc": "The stake was valued at $206,000",
                },
                {
                    "title": "레저캐피털매니지먼트, 2026년 2분기 프랭클린템플턴 XRP ETF 1만6745주 보유 공개",
                    "desc": "평가액은 20만6000달러로 집계됨",
                },
            ),
            (
                "state_department_adviser",
                {
                    "title": "US State Department appoints Bitcoin Policy Institute partner as adviser",
                    "desc": "The appointment adds a crypto policy specialist to the department",
                },
                {
                    "title": "미국 국무부, 비트코인정책연구소 파트너를 새 자문역으로 지명",
                    "desc": "암호화폐 정책 전문가가 국무부에 합류함",
                },
            ),
        )
        for name, first_story, second_story in pairs:
            with self.subTest(name=name):
                first = editor.build_story_signature(first_story)
                second = editor.build_story_signature(second_story)
                self.assertTrue(first)
                self.assertTrue(second)
                self.assertTrue(
                    editor._same_event(first, second),
                    msg=f"{name}\n{first}\n{second}",
                )

    def test_cross_language_amounts_are_normalized(self):
        comparisons = (
            ("$400 million", "4억달러", "amount_usd_400000000"),
            ("$9.7M", "970만달러", "amount_usd_9700000"),
            ("$206,000", "20만6000달러", "amount_usd_206000"),
        )
        for english, korean, expected in comparisons:
            with self.subTest(expected=expected):
                self.assertIn(expected, editor._amount_tokens(english))
                self.assertIn(expected, editor._amount_tokens(korean))
        self.assertIn("amount_btc_approx_620", editor._amount_tokens("623 BTC"))
        self.assertIn("amount_btc_approx_620", editor._amount_tokens("622.66BTC"))

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
        self.assertNotIn("#클래리티법안", footer)
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

    def test_generic_bill_in_clarity_story_becomes_clarity_tag(self):
        story = {
            "title": "CLARITY Act supporters seek votes before recess",
            "desc": "The crypto market structure bill still needs Senate votes",
        }
        summary = (
            "명확성 #법안 관계자는 비트코인 명확성을 위해 표를 확보할 수 있다고 밝힘\n\n"
            "업계는 #법안이 연내 처리될 가능성을 언급함"
        )
        tagged, _ = editor._inject_inline_tags(summary, story)
        self.assertEqual(tagged.count("#클래리티법안"), 1)
        self.assertTrue(tagged.startswith("#클래리티법안 관계자는"))
        self.assertNotIn("#법안", tagged)
        self.assertIn("업계는 클래리티법안이", tagged)

    def test_body_tags_are_not_repeated_in_footer(self):
        story = {
            "title": "Strategy STRC joins three US preferred stock ETFs",
            "desc": "The ETFs reported holdings in Strategy's STRC",
        }
        summary = "스트래티지의 STRC가 미국 우선주 ETF 3곳에 편입됨"
        tagged, selected = editor._inject_inline_tags(summary, story)
        self.assertIn("#스트래티지 의", tagged)
        self.assertIn("#ETF", tagged)

        footer = editor._build_footer_tags(story, selected)
        self.assertNotIn("#Strategy", footer)
        self.assertNotIn("#ETF", footer)

    def test_launch_price_performance_report_is_blocked(self):
        story = {
            "title": "Most high-value cryptocurrencies launched since 2024 trade below debut price",
            "desc": "CryptoRank says only 7% of major tokens outperform their launch price",
        }
        blocked, reason = editor._is_hard_blocked(story)
        self.assertTrue(blocked)
        self.assertIn("가격", reason)

    def test_sberbank_trading_infrastructure_is_cross_source_duplicate(self):
        first = {
            "title": "Sberbank builds regulated crypto trading infrastructure in Russia",
            "desc": "The bank plans to launch the system by December 1, 2026",
        }
        second = {
            "title": "스베르방크, 러시아 암호화폐 거래 인프라 구축",
            "desc": "2026년 12월 1일까지 규제형 디지털자산 거래 시스템을 만들어 출시할 계획",
        }
        first_signature = editor.build_story_signature(first)
        second_signature = editor.build_story_signature(second)
        self.assertTrue(first_signature)
        self.assertTrue(second_signature)
        self.assertIn("entity_스베르방크", first_signature)
        self.assertIn("object_regulated_trading_infrastructure", first_signature)
        self.assertTrue(editor._same_event(first_signature, second_signature))

    def test_sk_hynix_tokenization_uses_korean_first_mention_tags(self):
        story = {
            "title": "Exchanges launch SK Hynix ADR tokenization products in Korea",
            "desc": "Four tokenized SK Hynix products were issued for overseas investors",
        }
        summary = (
            "해외 거래소들이 SK하이닉스 ADR 기반 토큰화 상품을 출시하며 "
            "한국 주식 토큰 시장이 커지고 있다고 밝힘"
        )
        tagged, selected = editor._inject_inline_tags(summary, story)
        self.assertIn("#SK하이닉스", tagged)
        self.assertIn("#토큰화", tagged)
        self.assertIn("#한국", tagged)
        self.assertEqual(tagged.count("#SK하이닉스"), 1)
        footer = editor._build_footer_tags(story, selected)
        self.assertNotIn("#SKHynix", footer)
        self.assertNotIn("#Tokenization", footer)

    def test_support_level_weekend_market_story_is_blocked_twice(self):
        story = {
            "title": "Bitcoin holds $64,000 support as meme coin leads weekend market focus",
            "desc": "BTC defended the level while another token outperformed",
        }
        blocked, _ = editor._is_hard_blocked(story)
        self.assertTrue(blocked)
        self.assertTrue(
            editor._summary_is_market_only(
                "비트코인이 6만4000달러 지지선을 지키는 가운데 밈코인이 주말 시장을 주도함"
            )
        )

    def test_options_open_interest_story_is_blocked(self):
        story = {
            "title": "Bitcoin options open interest clusters around $70K and $72K",
            "desc": "Call options dominate bullish betting and account for 18% of the options market",
        }
        blocked, reason = editor._is_hard_blocked(story)
        self.assertTrue(blocked)
        self.assertIn("옵션", reason)
        self.assertTrue(
            editor._summary_is_market_only(
                "비트코인 옵션 미결제약정이 7만~7만2000달러 구간에 집중됨"
            )
        )

    def test_fear_greed_and_buying_pressure_story_is_blocked(self):
        stories = (
            {
                "title": "Bitcoin buying pressure improves as trading volume rises",
                "desc": "The crypto fear and greed index remains at 30",
            },
            {
                "title": "비트코인 매수세가 유입되며 거래량 증가",
                "desc": "공포탐욕지수는 여전히 공포 구간이라고 밝힘",
            },
        )
        for story in stories:
            with self.subTest(title=story["title"]):
                blocked, reason = editor._is_hard_blocked(story)
                self.assertTrue(blocked)
                self.assertIn("심리지수", reason)

    def test_news_roundup_and_rebound_story_is_blocked(self):
        story = {
            "title": "Ripple stablecoin and XRP ETF news roundup",
            "desc": "Ripple expanded stablecoin infrastructure but XRP failed to sustain its rebound",
        }
        blocked, reason = editor._is_hard_blocked(story)
        self.assertTrue(blocked)
        self.assertIn("추세", reason)
        self.assertTrue(
            editor._summary_is_market_only(
                "리플이 스테이블코인 인프라를 확대했지만 XRP는 최근 반등세를 지키지 못함"
            )
        )

    def test_wemix_story_is_blocked_even_with_target_assets(self):
        story = {
            "title": "WEMIX bridge services frozen after $724K USDC exploit",
            "desc": "Attackers moved funds through Ethereum and BNB Smart Chain",
        }
        self.assertIn("ETH", editor.target_assets(editor._story_text(story)))
        blocked, reason = editor._is_hard_blocked(story)
        self.assertTrue(blocked)
        self.assertIn("위믹스", reason)

    def test_middle_dot_is_spaced_only_at_hashtag_boundaries(self):
        text = "KRW·#비트코인·#USDT와 #SEC·#CFTC, 수수료는 0.14%임"
        self.assertEqual(
            editor.fix_hashtag_particles(text),
            "KRW· #비트코인 · #USDT 와 #SEC · #CFTC, 수수료는 0.14%임",
        )

    def test_new_company_tags_use_first_korean_mention_only(self):
        story = {
            "title": "Upbit lists RLUSD while Lido updates Ethereum validators",
            "desc": "Upbit and Lido published separate service updates",
        }
        summary = (
            "업비트가 RLUSD 거래를 지원하고 리도는 이더리움 검증자 업데이트를 공개함\n\n"
            "업비트와 리도는 적용 일정을 전함"
        )
        tagged, selected = editor._inject_inline_tags(summary, story)
        self.assertIn("#업비트 가", tagged)
        self.assertIn("#리도 는", tagged)
        self.assertEqual(tagged.count("#업비트"), 1)
        self.assertEqual(tagged.count("#리도"), 1)
        footer = editor._build_footer_tags(story, selected)
        self.assertNotIn("#Upbit", footer)
        self.assertNotIn("#Lido", footer)

    def test_technical_rate_and_old_proposal_cards_are_blocked(self):
        stories = (
            {
                "title": "Ethereum fails to break $2,000 resistance",
                "desc": "Forced liquidation sent ETH toward $1,900 as volatility concentrated near $1,850",
            },
            {
                "title": "Bitcoin pressured by Federal Reserve rate path",
                "desc": "The probability of a 25bp rate hike rose as markets feared a hawkish Fed",
            },
            {
                "title": "SHIB pulls back from the 100-day EMA",
                "desc": "Technical resistance may trigger a retracement despite higher volume",
            },
            {
                "title": "XRPL developers revisit a smart contract proposal from 2023",
                "desc": "Adoption remains undecided and no current launch or approval was announced",
            },
        )
        for story in stories:
            with self.subTest(title=story["title"]):
                blocked, _ = editor._is_hard_blocked(story)
                self.assertTrue(blocked)

    def test_mining_company_balance_sheet_story_is_blocked(self):
        story = {
            "title": "DCG mining subsidiary Foundry reshapes debt image",
            "desc": "The Bitcoin miner's revenue, intercompany loans and balance sheet were reviewed",
        }
        blocked, _ = editor._is_hard_blocked(story)
        self.assertTrue(blocked)

    def test_lido_validator_migration_variants_are_one_event(self):
        stories = (
            {
                "title": "Lido publishes Curated Module v2 and 0x02 withdrawal credential resources",
                "desc": "The Ethereum validator upgrade raises the active balance limit to 2,048 ETH",
            },
            {
                "title": "Lido moves staking infrastructure to Curated Module v2",
                "desc": "The validator credential migration cuts the validator count from 880,000 to 628,000",
            },
            {
                "title": "Lido Core 2026 consolidates validator structure",
                "desc": "Curated Module v2 combines validators and introduces operator collateral",
            },
        )
        signatures = [editor.build_story_signature(story) for story in stories]
        self.assertTrue(all(signatures))
        self.assertTrue(editor._same_event(signatures[0], signatures[1]))
        self.assertTrue(editor._same_event(signatures[0], signatures[2]))

    def test_fake_wallet_theft_matches_without_named_app(self):
        first = {
            "title": "Users sue Apple over fake Bitcoin wallet app",
            "desc": "Three users say a spoofed wallet stole $1,835,500 in the United States",
        }
        second = {
            "title": "가짜 비트코인 지갑 앱 피해자들 미국서 소송",
            "desc": "시드 문구를 입력한 이용자 3명에게서 183만5500달러 상당 BTC가 탈취됨",
        }
        first_signature = editor.build_story_signature(first)
        second_signature = editor.build_story_signature(second)
        self.assertIn("object_fake_wallet", first_signature)
        self.assertIn("object_fake_wallet", second_signature)
        self.assertTrue(editor._same_event(first_signature, second_signature))

    def test_morgan_stanley_leveraged_etf_variants_are_one_event(self):
        first = {
            "title": "Morgan Stanley launches leveraged Ethereum and Solana ETFs",
            "desc": "MSSE and MSOL begin trading with a 0.14% fee",
        }
        second = {
            "title": "모건스탠리, 이더리움·솔라나 레버리지 상품 출시",
            "desc": "상장지수상품 MSSE와 MSOL의 초기 자산은 각각 1억달러로 집계됨",
        }
        self.assertTrue(
            editor._same_event(
                editor.build_story_signature(first),
                editor.build_story_signature(second),
            )
        )

    def test_sbi_rebrand_variants_are_one_event(self):
        first = {
            "title": "SBI Holdings rebrands subsidiary as SBI Digital Factory",
            "desc": "The company transfers the Kent Network specialist finance business",
        }
        second = {
            "title": "SBI, 자회사 사명을 SBI 디지털 팩토리로 변경",
            "desc": "켄트 네트워크 전문 금융 사업을 새 법인으로 이전함",
        }
        self.assertTrue(
            editor._same_event(
                editor.build_story_signature(first),
                editor.build_story_signature(second),
            )
        )

    def test_flare_smart_account_and_fassets_plan_remain_distinct(self):
        smart_account = {
            "title": "Flare launches Smart Account v1.3",
            "desc": "The account lets XRP holders use FXRP and DeFi without manual bridging",
        }
        fassets_plan = {
            "title": "Flare CEO plans to integrate Bitcoin through FAssets",
            "desc": "FAssets will bring BTC liquidity to XRPL DeFi",
        }
        self.assertFalse(
            editor._same_event(
                editor.build_story_signature(smart_account),
                editor.build_story_signature(fassets_plan),
            )
        )

    def test_new_cross_source_event_families_are_duplicates(self):
        pairs = (
            (
                "hardware_wallet_security",
                {
                    "title": "Coldcard hardware wallet security flaw may expose user assets",
                    "desc": "A large security failure could cause up to $70 million in losses",
                },
                {
                    "title": "콜드카드 대형 보안 실패로 사용자 자산 손실 가능성 제기",
                    "desc": "피해 규모는 최대 7000만달러로 추산됨",
                },
            ),
            (
                "self_custody_lending",
                {
                    "title": "Uniswap launches Earn self-custodial lending product",
                    "desc": "USDC, USDT and ETH can be deposited into Morpho lending vaults",
                },
                {
                    "title": "유니스왑, 모포 대출 볼트 기반 자체 보관형 대출 상품 Earn 출시",
                    "desc": "USDC·USDT·ETH 예치를 지원함",
                },
            ),
            (
                "fake_investment_platform",
                {
                    "title": "Seoul police arrest three suspects behind fake XRP investment platform",
                    "desc": "The scheme took 3.4 million XRP from 71 victims",
                },
                {
                    "title": "서울경찰청, 가짜 XRP 투자 플랫폼 일당 3명 검거",
                    "desc": "피해자 71명에게서 340만 XRP를 가로챈 혐의를 받음",
                },
            ),
            (
                "foundation_governance",
                {
                    "title": "Ethereum Foundation appoints pcaversaccio to its board",
                    "desc": "The security researcher joined during a governance reshuffle",
                },
                {
                    "title": "이더리움 재단, 보안 연구자 pcaversaccio를 이사회 멤버로 임명",
                    "desc": "재단 거버넌스 재편의 일부로 진행됨",
                },
            ),
            (
                "named_stablecoin",
                {
                    "title": "BlackRock, Visa and Mastercard consortium launches OpenUSD",
                    "desc": "The Ethereum stablecoin is now official",
                },
                {
                    "title": "블랙록·비자·마스터카드 참여 컨소시엄, 오픈USD 출시 공식화",
                    "desc": "이더리움 기반 스테이블코인 출시를 발표함",
                },
            ),
            (
                "sovereign_reserve_mandate",
                {
                    "title": "Bhutan's Gelephu Mindfulness City appoints 3iQ",
                    "desc": "The Canadian manager will manage part of the national Bitcoin reserve",
                },
                {
                    "title": "부탄 겔레푸 마인드풀니스 시티, 3iQ를 비트코인 국고 운용사로 지정",
                    "desc": "국가 보유 BTC 일부의 운용을 맡김",
                },
            ),
            (
                "preferred_stock_redemption",
                {
                    "title": "Strategy launches cash redemption program for preferred shares",
                    "desc": "The company set aside $390 million for redemptions",
                },
                {
                    "title": "스트래티지, 비트코인 현금화 뒤 우선주 현금 상환 프로그램 시작",
                    "desc": "상환용 현금 3억9000만달러를 준비함",
                },
            ),
            (
                "anonymous_cashback_card",
                {
                    "title": "Bitcoin Yield card launches global cashback program",
                    "desc": "Users in 100 countries can earn 3% cashback on up to $50,000",
                },
                {
                    "title": "비트코인 월릿 카드 이용자용 캐시백 프로그램 전 세계 출시",
                    "desc": "100개국에서 최대 5만달러의 3%를 캐시백으로 제공함",
                },
            ),
        )
        for name, first_story, second_story in pairs:
            with self.subTest(name=name):
                first = editor.build_story_signature(first_story)
                second = editor.build_story_signature(second_story)
                self.assertTrue(first, msg=name)
                self.assertTrue(second, msg=name)
                self.assertTrue(editor._same_event(first, second), msg=f"{name}\n{first}\n{second}")

    def test_similar_event_types_with_different_anchors_stay_distinct(self):
        distinct_pairs = (
            (
                {
                    "title": "Coldcard hardware wallet security flaw risks $70 million",
                    "desc": "The issue affects Bitcoin users",
                },
                {
                    "title": "Coldcard patches a separate hardware wallet vulnerability",
                    "desc": "The later issue risks $2 million in Bitcoin",
                },
            ),
            (
                {
                    "title": "Ethereum Foundation appoints pcaversaccio to its board",
                    "desc": "The security researcher joins the foundation governance team",
                },
                {
                    "title": "Ethereum Foundation appoints Alice Example to its board",
                    "desc": "A different researcher joins in a later governance change",
                },
            ),
            (
                {
                    "title": "Bitcoin rewards card launches in 100 countries",
                    "desc": "The card offers 3% cashback on up to $50,000",
                },
                {
                    "title": "Another Bitcoin rewards card launches a cashback service",
                    "desc": "The separate card offers 3% cashback",
                },
            ),
        )
        for first_story, second_story in distinct_pairs:
            with self.subTest(first=first_story["title"]):
                self.assertFalse(
                    editor._same_event(
                        editor.build_story_signature(first_story),
                        editor.build_story_signature(second_story),
                    )
                )


if __name__ == "__main__":
    unittest.main()
