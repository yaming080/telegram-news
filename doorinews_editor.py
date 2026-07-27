"""Stable editorial rules for the DooriNews Telegram bot.

This module deliberately owns the final filtering, event deduplication, summary
formatting, inline tags, and footer tags.  The collector and Telegram delivery
remain in ``doorinews_bot.py``.
"""

from __future__ import annotations

import html
import hashlib
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Callable, Iterable


FIXED_FOOTER_TAGS = (
    "#BTC",
    "#비트코인",
    "#dooridoori",
    "#도리도리",
    "#doorinati",
    "#도리나티",
)

MAX_INLINE_TAGS = 5
MAX_ARTICLE_TAGS = 4
TARGET_SUMMARY_CHARS = 155
HARD_SUMMARY_CHARS = 210

_RUNTIME: dict = {}
_PREVIOUS_MATCHES: Callable | None = None


@dataclass(frozen=True)
class EntitySpec:
    kind: str
    label: str
    aliases: tuple[str, ...]
    footer: str = ""
    priority: int = 50


ENTITY_SPECS = (
    # Countries and regions: Korean in the body, omitted from the footer.
    EntitySpec("geo", "미국", ("United States", "U.S.", "USA", "미국"), priority=10),
    EntitySpec("geo", "한국", ("South Korea", "Korea", "대한민국", "한국"), priority=10),
    EntitySpec("geo", "일본", ("Japan", "Japanese", "일본"), priority=10),
    EntitySpec("geo", "러시아", ("Russia", "Russian", "러시아"), priority=10),
    EntitySpec("geo", "유럽연합", ("European Union", "EU", "유럽연합"), priority=10),
    EntitySpec("geo", "영국", ("United Kingdom", "UK", "Britain", "영국"), priority=10),
    EntitySpec("geo", "중국", ("China", "Chinese", "중국"), priority=10),
    EntitySpec("geo", "홍콩", ("Hong Kong", "홍콩"), priority=10),
    EntitySpec("geo", "싱가포르", ("Singapore", "싱가포르"), priority=10),
    EntitySpec("geo", "부탄", ("Bhutan", "부탄"), priority=10),
    EntitySpec("geo", "인도", ("India", "Indian", "인도"), priority=10),
    EntitySpec("geo", "말레이시아", ("Malaysia", "Malaysian", "말레이시아"), priority=10),
    EntitySpec("geo", "필리핀", ("Philippines", "Philippine", "필리핀"), priority=10),
    EntitySpec("geo", "독일", ("Germany", "German", "독일"), priority=10),
    EntitySpec("geo", "이탈리아", ("Italy", "Italian", "이탈리아"), priority=10),
    EntitySpec("geo", "스페인", ("Spain", "Spanish", "스페인"), priority=10),
    EntitySpec("geo", "호주", ("Australia", "Australian", "호주"), priority=10),
    EntitySpec("geo", "튀르키예", ("Turkey", "Turkish", "Türkiye", "튀르키예"), priority=10),
    EntitySpec("geo", "두바이", ("Dubai", "두바이"), priority=10),
    # Regulators, companies, and institutions.
    EntitySpec("org", "SEC", ("SEC", "Securities and Exchange Commission"), "#SEC", 20),
    EntitySpec("org", "CFTC", ("CFTC", "Commodity Futures Trading Commission"), "#CFTC", 20),
    EntitySpec("org", "FCA", ("FCA", "Financial Conduct Authority"), "#FCA", 20),
    EntitySpec("org", "OCC", ("OCC", "Office of the Comptroller of the Currency"), "#OCC", 20),
    EntitySpec("org", "IMF", ("IMF", "International Monetary Fund", "국제통화기금"), "#IMF", 20),
    EntitySpec("org", "홍콩금융관리국", ("HKMA", "Hong Kong Monetary Authority", "홍콩금융관리국"), "#HKMA", 20),
    EntitySpec("org", "연준", ("Federal Reserve", "Fed", "연방준비제도", "연준"), "#FederalReserve", 20),
    EntitySpec("org", "HTX", ("HTX", "Huobi", "후오비"), "#HTX", 20),
    EntitySpec("org", "모건스탠리", ("Morgan Stanley", "모건스탠리"), "#MorganStanley", 20),
    EntitySpec("org", "갤럭시리서치", ("Galaxy Research", "갤럭시리서치"), "#GalaxyResearch", 20),
    EntitySpec("org", "비트멕스", ("BitMEX", "비트멕스"), "#BitMEX", 20),
    EntitySpec("org", "로빈후드", ("Robinhood", "로빈후드"), "#Robinhood", 20),
    EntitySpec("org", "문페이", ("MoonPay", "문페이"), "#MoonPay", 20),
    EntitySpec("org", "디스커버", ("Discover", "Discover Card", "디스커버"), "#Discover", 20),
    EntitySpec("org", "리플", ("Ripple", "리플"), "#Ripple", 20),
    EntitySpec("org", "XRPL재단", ("XRPL Foundation", "XRP Ledger Foundation", "XRPL재단"), "#XRPLFoundation", 20),
    EntitySpec("org", "SBI", ("SBI Holdings", "SBI", "에스비아이"), "#SBI", 20),
    EntitySpec("org", "라쿠텐", ("Rakuten", "라쿠텐"), "#Rakuten", 20),
    EntitySpec("org", "미래에셋", ("Mirae Asset", "미래에셋"), "#MiraeAsset", 20),
    EntitySpec("org", "코빗", ("Korbit", "코빗"), "#Korbit", 20),
    EntitySpec("org", "디지털엑스", ("Digital X", "DigitalX", "디지털엑스"), "#DigitalX", 20),
    EntitySpec("org", "마이크로소프트", ("Microsoft", "마이크로소프트"), "#Microsoft", 20),
    EntitySpec("org", "코인베이스", ("Coinbase", "코인베이스"), "#Coinbase", 20),
    EntitySpec("org", "바이낸스", ("Binance", "바이낸스"), "#Binance", 20),
    EntitySpec("org", "바이비트", ("Bybit", "바이비트"), "#Bybit", 20),
    EntitySpec("org", "블랙록", ("BlackRock", "Blackrock", "블랙록"), "#BlackRock", 20),
    EntitySpec("org", "프랭클린템플턴", ("Franklin Templeton", "FranklinTempleton", "프랭클린 템플턴", "프랭클린템플턴"), "#FranklinTempleton", 20),
    EntitySpec("org", "JP모건", ("JPMorgan", "J.P. Morgan", "JP Morgan", "JP모건"), "#JPMorgan", 20),
    EntitySpec("org", "뱅크오브아메리카", ("Bank of America", "뱅크오브아메리카"), "#BankOfAmerica", 20),
    EntitySpec("org", "스탠다드차타드", ("Standard Chartered", "스탠다드차타드"), "#StandardChartered", 20),
    EntitySpec("org", "앤드리슨호로위츠", ("Andreessen Horowitz", "a16z", "앤드리슨호로위츠"), "#AndreessenHorowitz", 20),
    EntitySpec("org", "HSBC", ("HSBC",), "#HSBC", 20),
    EntitySpec("org", "KB국민은행", ("KB Kookmin Bank", "Kookmin Bank", "KB국민은행"), "#KookminBank", 20),
    EntitySpec("org", "마스터카드", ("Mastercard", "MasterCard", "마스터카드"), "#Mastercard", 20),
    EntitySpec("org", "아베", ("Aave", "아베"), "#Aave", 20),
    EntitySpec("org", "아이렌", ("IREN", "Iris Energy", "아이렌"), "#IREN", 20),
    EntitySpec("org", "BC카드", ("BC Card", "BC카드"), "#BCCard", 20),
    EntitySpec("org", "카르다노", ("Cardano", "카르다노"), "#Cardano", 20),
    EntitySpec("org", "테더", ("Tether", "테더"), "#Tether", 20),
    EntitySpec("org", "스트래티지", ("Strategy", "MicroStrategy", "스트래티지"), "#Strategy", 20),
    EntitySpec("org", "오픈AI", ("OpenAI", "오픈AI", "오픈에이아이"), "#OpenAI", 20),
    EntitySpec("org", "앤트로픽", ("Anthropic", "앤트로픽"), "#Anthropic", 20),
    EntitySpec("org", "OKX", ("OKX",), "#OKX", 20),
    EntitySpec("org", "풀린", ("Poolin", "풀린"), "#Poolin", 20),
    EntitySpec("org", "시타델증권", ("Citadel Securities", "시타델 증권", "시타델증권"), "#CitadelSecurities", 20),
    EntitySpec("org", "아비트럼", ("Arbitrum", "아비트럼"), "#Arbitrum", 20),
    EntitySpec("org", "유니스왑", ("Uniswap", "유니스왑"), "#Uniswap", 20),
    EntitySpec("org", "트리플A", ("Triple-A", "Triple A", "TripleA", "트리플A", "트리플에이"), "#TripleA", 20),
    EntitySpec("org", "탱고", ("DEX Tango", "Tango DEX", "Tango", "탱고"), "#Tango", 20),
    EntitySpec("org", "스트라이브", ("Strive", "스트라이브"), "#Strive", 20),
    EntitySpec("org", "레저캐피털매니지먼트", ("Ledger Capital Management", "레저 캐피털 매니지먼트", "레저캐피털매니지먼트"), "#LedgerCapitalManagement", 20),
    EntitySpec("org", "비트코인정책연구소", ("Bitcoin Policy Institute", "BPI", "비트코인정책연구소"), "#BitcoinPolicyInstitute", 20),
    EntitySpec("org", "미국국무부", ("U.S. State Department", "US State Department", "State Department", "미국 국무부", "국무부"), "#USStateDepartment", 20),
    EntitySpec("org", "스베르방크", ("Sberbank", "Sber Bank", "스베르방크"), "#Sberbank", 20),
    EntitySpec("org", "SK하이닉스", ("SK hynix", "SK Hynix", "SK하이닉스"), "#SKHynix", 20),
    # People.
    EntitySpec("person", "저스틴선", ("Justin Sun", "저스틴 선", "저스틴선"), "#JustinSun", 15),
    EntitySpec("person", "아서헤이즈", ("Arthur Hayes", "아서 헤이즈", "아서헤이즈"), "#ArthurHayes", 15),
    EntitySpec("person", "블라드테네프", ("Vlad Tenev", "블라드 테네프", "블라드테네프"), "#VladTenev", 15),
    EntitySpec("person", "데이비드슈워츠", ("David Schwartz", "데이비드 슈워츠", "데이비드슈워츠"), "#DavidSchwartz", 15),
    EntitySpec("person", "마이클세일러", ("Michael Saylor", "마이클 세일러", "마이클세일러"), "#MichaelSaylor", 15),
    EntitySpec("person", "도널드트럼프", ("Donald Trump", "Trump", "도널드 트럼프", "트럼프"), "#DonaldTrump", 15),
    EntitySpec("person", "헤스터피어스", ("Hester Peirce", "헤스터 피어스", "헤스터피어스"), "#HesterPeirce", 15),
    EntitySpec("person", "찰스호스킨슨", ("Charles Hoskinson", "찰스 호스킨슨", "찰스호스킨슨"), "#CharlesHoskinson", 15),
    EntitySpec("person", "브래드갈링하우스", ("Brad Garlinghouse", "브래드 갈링하우스", "브래드갈링하우스"), "#BradGarlinghouse", 15),
    EntitySpec("person", "제이미다이먼", ("Jamie Dimon", "제이미 다이먼", "제이미다이먼"), "#JamieDimon", 15),
    EntitySpec("person", "피터쉬프", ("Peter Schiff", "피터 쉬프", "피터쉬프"), "#PeterSchiff", 15),
    EntitySpec("person", "일론머스크", ("Elon Musk", "일론 머스크", "일론머스크"), "#ElonMusk", 15),
    EntitySpec("person", "파벨두로프", ("Pavel Durov", "파벨 두로프", "파벨두로프"), "#PavelDurov", 15),
    EntitySpec("person", "짐크레이머", ("Jim Cramer", "짐 크레이머", "짐크레이머"), "#JimCramer", 15),
    EntitySpec("person", "크리스틴스미스", ("Kristin Smith", "크리스틴 스미스", "크리스틴스미스"), "#KristinSmith", 15),
    EntitySpec("person", "데이비드솔로몬", ("David Solomon", "데이비드 솔로몬", "데이비드솔로몬"), "#DavidSolomon", 15),
    # Assets, laws, and concrete products.
    EntitySpec("asset", "XRP", ("XRP",), "#XRP", 30),
    EntitySpec("asset", "XRPL", ("XRP Ledger", "XRPL",), "#XRPL", 30),
    EntitySpec("asset", "비트코인", ("Bitcoin", "BTC", "비트코인"), "", 30),
    EntitySpec("asset", "이더리움", ("Ethereum", "ETH", "이더리움"), "#ETH", 30),
    EntitySpec("asset", "솔라나", ("Solana", "SOL", "솔라나"), "#SOL", 30),
    EntitySpec("asset", "USDT", ("USDT",), "#USDT", 30),
    EntitySpec("asset", "USDC", ("USDC",), "#USDC", 30),
    EntitySpec("asset", "RLUSD", ("RLUSD",), "#RLUSD", 30),
    EntitySpec("topic", "ETF", ("ETF", "exchange-traded fund"), "#ETF", 35),
    EntitySpec("topic", "스테이블코인", ("stablecoin", "stablecoins", "스테이블코인"), "#Stablecoin", 35),
    EntitySpec("topic", "토큰화", ("tokenization", "tokenized", "토큰화"), "#Tokenization", 35),
    EntitySpec("topic", "클래리티법안", ("CLARITY Act", "CLARITY", "market structure bill", "시장구조법안", "클래리티법", "클래리티법안"), "#클래리티법안", 25),
    EntitySpec("topic", "지니어스법안", ("GENIUS Act", "지니어스법안"), "#GeniusAct", 25),
    EntitySpec("topic", "AI", ("artificial intelligence", "AI", "인공지능"), "#AI", 40),
    EntitySpec("topic", "IPO", ("IPO", "initial public offering"), "#IPO", 40),
    EntitySpec("topic", "X", ("X account", "X post", "X platform", "엑스 계정", "엑스 게시물"), "#X", 40),
)


EXCLUDED_MARKET_CONTENT_PATTERNS = (
    # Derivatives positioning and open-interest cards.
    r"\bopen\s+interest\b",
    r"\boptions?\s+market\b",
    r"\b(?:call|put)\s+options?\b",
    r"\boptions?\b.{0,55}\b(?:strike|expiry|expiration|betting|positioning|volume)\b",
    r"\b(?:strike|expiry|expiration|betting|positioning)\b.{0,55}\boptions?\b",
    r"미결제\s*약정|옵션\s*시장|옵션\s*(?:거래|베팅|만기|행사가)|콜\s*옵션|풋\s*옵션",
    # Sentiment, buying-pressure, and market-direction commentary.
    r"\b(?:crypto\s+)?fear\s*(?:and|&|/|-)\s*greed\s+index\b",
    r"\b(?:fear|greed)\s+index\b",
    r"\b(?:buy|buying)\s+(?:pressure|momentum|interest)\b",
    r"\b(?:rebound|rebounds|rebounded|rebounding|bounce|bounces|bounced)\b",
    r"\b(?:downtrend|downward\s+trend|bearish\s+trend|bearish\s+momentum)\b",
    r"공포\s*(?:탐욕|·\s*탐욕|및\s*탐욕)\s*지수|공포\s*지수|탐욕\s*지수",
    r"매수세|매수\s*(?:압력|우위|모멘텀)",
    r"반등세|반등|하락세|내림세|약세\s*흐름",
    # Multi-topic cards and the operator-excluded WEMIX ecosystem.
    r"\bnews\s+roundup\b",
    r"뉴스\s*(?:라운드업|모음)",
    r"\bwemix\$?\b",
    r"위믹스|윔엑스",
)


HARD_BLOCK_PATTERNS = (
    r"\bprice prediction\b",
    r"\btechnical analysis\b",
    r"\bsupport level\b",
    r"\bresistance level\b",
    r"\bprice target\b",
    r"\bnext bullish wave\b",
    r"\bwhat(?:'s| is) next\b",
    r"\bwill .{0,30} reach \$?\d",
    r"\bbest (?:crypto|memecoin|token)s? to buy\b",
    r"\bpresale\b",
    r"\bairdrop\b",
    r"\bpromo(?:tion)?\b",
    r"\bsponsored\b",
    r"\bmarket (?:review|update|outlook)\b",
    r"\bweekly crypto (?:digest|roundup)\b",
    r"\btop weekly crypto news\b",
    r"\bhere'?s what happened in crypto today\b",
    r"\bcrypto biz\b",
    r"\bai[- ]to[- ]crypto rotation\b",
    r"\bquantum roadmap\b.{0,45}\b(?:bitcoin|btc)\b",
    r"\bpush bitcoin much higher\b",
    r"\bliquidation imbalance\b",
    r"\blongs? lose\b",
    r"\bshorts? lose\b",
    r"\bbear trap\b",
    r"\bbull trap\b",
    r"\bcritical test\b",
    r"\brejection at resistance\b",
    r"\bresistance\b.{0,45}\bprice\b",
    r"\bbear market\b.{0,45}\b(?:over|recovery|profit)\b",
    r"\bsupply returns? to profit\b",
    r"\baccumulation window\b",
    r"\bsharpe ratio\b",
    r"\bmandatory .{0,20} migration\b",
    r"\bhistoric fork\b",
    r"\bworld foundation\b.{0,80}\b(?:funding|token sale|world id)\b",
    r"\bwld token sale\b",
    r"\b(?:stock|shares?|preferred stock|sata|strc)\b.{0,70}\b(?:rebound|recovery|recover(?:ed|s)?|rise|rises|gain|gains|upside)\b",
    r"\b(?:rebound|recovery|recover(?:ed|s)?|rise|rises|gain|gains|upside)\b.{0,70}\b(?:stock|shares?|preferred stock|sata|strc)\b",
    r"(?:우선주|SATA|STRC).{0,35}(?:반등|회복|주가|액면가|상승)",
    r"(?:반등|회복|주가|액면가|상승).{0,35}(?:우선주|SATA|STRC)",
    r"\b(?:tokens?|coins?|cryptocurrenc(?:y|ies)|altcoins?)\b.{0,100}\b(?:trade|trades|trading)\b.{0,45}\bbelow\b.{0,35}\b(?:launch|listing|debut|issue)\s+price\b",
    r"\b(?:launch|listing|debut|issue)\s+price\b.{0,70}\b(?:below|underperform|outperform)\b",
    r"(?:암호화폐|토큰|알트코인).{0,55}출시가(?:보다|를|에).{0,35}(?:낮|밑|아래|웃돌)",
    r"(?:출시가를\s*웃도는\s*비중|대부분.{0,35}출시가.{0,25}(?:낮|아래|밑))",
    r"\b(?:bitcoin|btc|ethereum|eth|xrp)\b.{0,40}\b(?:holds?|defends?|maintains?)\b.{0,25}\$?[\d,]+",
    r"\b(?:weekend\s+(?:market\s+)?focus|meme(?:coin)?s?\b.{0,35}\b(?:leads?|outperform))\b",
    r"(?:비트코인|BTC|이더리움|ETH|XRP).{0,35}\d[\d,]*\s*달러.{0,25}(?:지지|유지|방어)",
    r"\bdex aggregator\b.{0,40}\bshut down\b",
    r"\bprotocol to shut down\b",
    r"\bkazakhstan\b.{0,100}\b(?:crypto|bitcoin|btc)\b.{0,100}\b(?:miner|mining)\b.{0,100}\b(?:electricity|power|energy|tariff|fee|rate)\b",
    r"\b(?:crypto|bitcoin|btc)\b.{0,100}\b(?:miner|mining)\b.{0,100}\b(?:electricity|power|energy|tariff|fee|rate)\b.{0,100}\bkazakhstan\b",
    r"\bwhales? control\b",
    r"\bwallets? (?:add|added|hold|holding)\b",
    r"\bexchange (?:inflow|outflow|withdrawal)s?\b",
    r"\bup \d+(?:\.\d+)?%\b",
    r"\bdown \d+(?:\.\d+)?%\b",
    r"\bfalls? \d+(?:\.\d+)?%\b",
    r"\bdrops? \d+(?:\.\d+)?%\b",
    r"가격\s*전망",
    r"기술적\s*분석",
    r"지지선|저항선",
    r"매수\s*추천",
    r"프리세일|에어드롭",
    r"주간\s*(?:뉴스|다이제스트|요약)",
    r"롱\s*포지션|숏\s*포지션|대규모\s*청산",
    r"상승\s*가능성|하락\s*가능성",
    r"몇\s*배\s*(?:상승|오를)",
    r"베어마켓|약세장.{0,20}(?:종료|회복)",
)

TECHNICAL_SUMMARY_PATTERNS = (
    r"\b(?:support|resistance)\s+level\b",
    r"\b(?:bitcoin|btc|ethereum|eth|xrp)\b.{0,45}\b(?:holds?|defends?|maintains?)\b.{0,25}\$?[\d,]+",
    r"\bweekend\s+(?:market\s+)?focus\b",
    r"지지선|저항선",
    r"(?:비트코인|BTC|이더리움|ETH|XRP).{0,35}\d[\d,]*\s*달러.{0,25}(?:지지|유지|방어)",
    r"(?:가격|시장).{0,20}(?:지키는|지켰|방어).{0,20}(?:가운데|반면)",
    r"주말\s*시장의?\s*(?:중심|주도)",
)

CRYPTO_CORE_PATTERNS = (
    r"\bbitcoin\b", r"\bbtc\b", r"\bethereum\b", r"\beth\b", r"\bxrp\b",
    r"\bxrpl\b", r"\bcrypto(?:currency)?\b", r"\bblockchain\b", r"\bstablecoin\b",
    r"\busdt\b", r"\busdc\b", r"\bdefi\b", r"\bweb3\b", r"\btokenization\b",
    r"비트코인|이더리움|암호화폐|블록체인|스테이블코인|토큰화|디지털자산",
)

# DooriNews now follows only the assets explicitly selected by the operator.
# Publisher names, generic "crypto" wording, and the fixed #BTC footer are not
# evidence that an article belongs to this list.
TARGET_ASSET_PATTERNS = {
    "BTC": (r"(?<![a-z0-9])btc(?![a-z0-9])", r"\bbitcoin\b", r"비트코인"),
    "ETH": (r"(?<![a-z0-9])eth(?![a-z0-9])", r"\bethereum\b", r"이더리움(?!\s*클래식)"),
    "XRP": (r"(?<![a-z0-9])xrp(?![a-z0-9])", r"\bripple\b", r"\bxrpl\b", r"\bxrp ledger\b", r"리플|엑스알피"),
    "XLM": (r"(?<![a-z0-9])xlm(?![a-z0-9])", r"\bstellar(?: lumens?)?\b", r"스텔라(?:루멘)?"),
    "BCH": (r"(?<![a-z0-9])bch(?![a-z0-9])", r"\bbitcoin cash\b", r"비트코인\s*캐시"),
    "ETC": (r"(?<![a-z0-9])etc(?![a-z0-9])", r"\bethereum classic\b", r"이더리움\s*클래식"),
    "TRX": (r"(?<![a-z0-9])trx(?![a-z0-9])", r"\btron\b", r"트론"),
    "ADA": (r"(?<![a-z0-9])ada(?![a-z0-9])", r"\bcardano\b", r"에이다|카르다노"),
    "BNB": (r"(?<![a-z0-9])bnb(?![a-z0-9])", r"\bbinance coin\b", r"바이낸스\s*코인"),
    "SHIB": (r"(?<![a-z0-9])shib(?![a-z0-9])", r"\bshiba inu\b", r"\bshibarium\b", r"시바이누|시바리움"),
    "FLR": (r"(?<![a-z0-9])flr(?![a-z0-9])", r"\bflare(?: network)?\b", r"플레어"),
    "ENA": (r"(?<![a-z0-9])ena(?![a-z0-9])", r"\bethena\b", r"에테나"),
}

# These are recurring market-statistic cards rather than concrete news events.
# Block them even when a target asset such as BTC or ETH is mentioned.
LOW_VALUE_FLOW_PATTERNS = (
    r"\b(?:spot\s+)?(?:bitcoin|btc|ethereum|eth)?\s*etfs?\b.{0,90}\b(?:net\s+)?(?:inflows?|outflows?|flows?)\b",
    r"\b(?:net\s+)?(?:inflows?|outflows?)\b.{0,90}\b(?:spot\s+)?(?:bitcoin|btc|ethereum|eth)?\s*etfs?\b",
    r"\b(?:records?|posts?|sees?|ends?|closes?)\b.{0,45}\b(?:\d+\s*(?:day|week)s?\s+)?(?:consecutive\s+)?(?:inflows?|outflows?)\b",
    r"\b(?:consecutive|straight)\s+\d*\s*(?:day|week|session|trading day)s?\s+(?:of\s+)?(?:inflows?|outflows?)\b",
    r"\bweekly\s+(?:close|closing|flows?|inflows?|outflows?|fund flows?)\b",
    r"\bweek(?:ly)?\b.{0,45}\b(?:net\s+)?(?:inflows?|outflows?)\b",
    r"(?:비트코인|이더리움|BTC|ETH)?\s*ETF.{0,45}(?:순유입|순유출|자금\s*유입|자금\s*유출|유입\s*흐름|유출\s*흐름)",
    r"(?:순유입|순유출|연속\s*유입|연속\s*유출|자금\s*흐름).{0,45}(?:ETF|상장지수펀드)",
    r"(?:\d+\s*거래일|\d+\s*주|\d+\s*일)\s*연속\s*(?:유입|유출)",
    r"주간\s*(?:마감|종가|순유입|순유출|자금\s*흐름)",
)

CONCRETE_EVENT_PATTERNS = (
    r"\bapprov(?:e|ed|al)\b", r"\bpass(?:ed|es)?\b", r"\bfile(?:d|s|ing)?\b",
    r"\bappoint(?:ed|ment)?\b", r"\bnomina(?:te|ted|tion)\b",
    r"\blaunch(?:ed|es)?\b", r"\bintroduc(?:e|ed|tion)\b", r"\broll(?:ed)? out\b",
    r"\bpartner(?:ed|ship)?\b", r"\bintegrat(?:e|ed|ion)\b",
    r"\bacquir(?:e|ed|es|ing)\b", r"\binvest(?:ed|ment|s)?\b",
    r"\bpatent\b", r"\blicen[cs](?:e|ed|ing)\b", r"\bregister(?:ed|s)?\b",
    r"\bdisclos(?:e|es|ed|ure)\b", r"\bpublish(?:ed|es)?\b", r"\bannounce(?:d|s)?\b",
    r"\bissue(?:d|s|ance)?\b", r"\badopt(?:ed|ion)?\b", r"\bdeploy(?:ed|ment)?\b",
    r"\brestore(?:d|s)?\b", r"\barrest(?:ed|s)?\b", r"\bcharg(?:e|ed|es)\b",
    r"\b(?:shut(?:s|ting)?\s+down|shutdown|clos(?:e|ed|es|ing|ure))\b",
    r"\b(?:chapter\s*11|bankruptcy|bankrupt|auction(?:ed|s|ing)?)\b",
    r"\bmint(?:ed|s|ing)?\b",
    r"\bsue(?:d|s)?\b", r"\blawsuit\b", r"\bsettle(?:d|ment)?\b",
    r"\bhack(?:ed|s)?\b", r"\bexploit(?:ed|s)?\b", r"\brecover(?:ed|y)?\b",
    r"\bsanction(?:ed|s)?\b", r"\bback(?:ed|s|ing)?\b", r"\bsupport(?:ed|s|ing)?\b",
    r"\brefin(?:e|ed|es|ing)\b", r"\bdevelop(?:ed|s|ing|ment)?\b",
    r"\bcut(?:s)?\b.{0,35}\b(?:odds|probability|estimate)\b",
    r"\blower(?:ed|s|ing)?\b.{0,35}\b(?:odds|probability|estimate)\b",
    r"승인|통과|제출|신청|임명|지명|출시|도입|공개|발표|제휴|협력|통합",
    r"인수|투자|특허|인가|등록|발행|배포|복구|체포|기소|소송|합의|해킹|익스플로잇",
    r"제재|지지|개발|개선|확률.{0,15}(?:하향|낮춤|축소)",
    r"폐쇄|운영\s*종료|서비스\s*종료|파산|챕터\s*11|경매|민트",
)

ACTION_PATTERNS = {
    "action_approve": (r"\bapprov(?:e|ed|al)\b", r"승인|인가"),
    "action_pass": (r"\bpass(?:ed|es)?\b", r"통과"),
    "action_file": (r"\bfile(?:d|s|ing)?\b", r"제출|신청|신고"),
    "action_appoint": (r"\bappoint(?:ed|ment)?\b", r"\bnomina(?:te|ted|tion)\b", r"임명|지명|합류"),
    "action_launch": (r"\blaunch(?:ed|es)?\b", r"\broll(?:ed)? out\b", r"출시|도입|공개"),
    "action_partner": (r"\bpartner(?:ed|ship)?\b", r"제휴|협력|협약"),
    "action_acquire": (r"\bacquir(?:e|ed|es|ing)\b", r"인수|확보"),
    "action_secure": (r"\bsecur(?:e|ed|es|ing)\b", r"\bobtain(?:ed|s)?\b", r"\bwins?\b", r"확보|취득"),
    "action_invest": (r"\binvest(?:ed|ment|s)?\b", r"투자"),
    "action_issue": (r"\bissue(?:d|s|ance)?\b", r"발행"),
    "action_disclose": (r"\bdisclos(?:e|es|ed|ure)\b", r"공개|공시"),
    "action_restore": (r"\brestore(?:d|s)?\b", r"복구|재개"),
    "action_bankruptcy": (
        r"\b(?:file(?:d|s|ing)?\s+for\s+)?(?:chapter\s*11|bankruptcy|bankrupt)\b",
        r"챕터\s*11|파산\s*보호|파산\s*신청|파산함|파산",
    ),
    "action_auction": (r"\bauction(?:ed|s|ing)?\b", r"경매|매각"),
    "action_publish": (
        r"\bpublish(?:ed|es|ing)?\b",
        r"\breleas(?:e|ed|es|ing)\b.{0,25}\breport\b",
        r"보고서.{0,15}(?:공개|발표|발간)|최종\s*보고서",
    ),
    "action_mint": (r"\bmint(?:ed|s|ing)?\b", r"민트|발행"),
    "action_close": (
        r"\b(?:shut(?:s|ting)?\s+down|shutdown|clos(?:e|ed|es|ing|ure)|"
        r"ceas(?:e|ed|es|ing)\s+operations|terminat(?:e|ed|es|ing|ion)\s+operations|"
        r"end(?:s|ed|ing)?\s+(?:service|network|operations))\b",
        r"폐쇄|운영\s*종료|영구\s*종료|서비스\s*종료|네트워크\s*종료",
    ),
    "action_enforce": (r"\barrest(?:ed|s)?\b", r"\bcharg(?:e|ed|es)\b", r"\bfine(?:d|s)?\b", r"체포|기소|제재|벌금"),
    "action_sue": (r"\bsue(?:d|s)?\b", r"\blawsuit\b", r"\bclass action\b", r"소송|고소"),
    "action_hack": (
        r"\bhack(?:ed|s)?\b",
        r"\bexploit(?:ed|s)?\b",
        r"\b(?:hot\s+wallet|crypto\s+wallet)\b.{0,40}\b(?:attack(?:ed)?|drain(?:ed|s)?)\b",
        r"해킹|익스플로잇|핫월렛.{0,30}(?:공격|탈취)|의심\s*공격",
    ),
    "action_ban": (r"\bban(?:ned|s)?\b", r"\brestrict(?:ed|s|ion)?\b", r"금지|제한"),
    "action_deny": (r"\bden(?:y|ies|ied)\b", r"\bdisput(?:e|ed|es)\b", r"\brefut(?:e|ed|es)\b", r"부인|반박"),
    "action_convert": (r"\bconvert(?:ed|s|ing)?\b", r"\btransition(?:ed|s|ing)?\b", r"전환"),
    "action_sanction": (r"\bsanction(?:ed|s)?\b", r"제재"),
    "action_support": (r"\bback(?:ed|s|ing)?\b", r"\bsupport(?:ed|s|ing)?\b", r"지지"),
    "action_develop": (r"\brefin(?:e|ed|es|ing)\b", r"\bdevelop(?:ed|s|ing|ment)?\b", r"개발|개선"),
    "action_build": (
        r"\bbuild(?:s|ing|t)?\b",
        r"\bconstruct(?:s|ed|ing|ion)?\b",
        r"\bset(?:s|ting)?\s+up\b",
        r"구축|설립|정비|만들(?:고|어|었|기로)",
    ),
    "action_revise": (
        r"\bcut(?:s)?\b.{0,35}\b(?:odds|probability|estimate)\b",
        r"\blower(?:ed|s|ing)?\b.{0,35}\b(?:odds|probability|estimate)\b",
        r"확률.{0,15}(?:하향|낮춤|축소)",
    ),
}

OBJECT_PATTERNS = {
    "object_etf": (r"\betf\b", r"상장지수펀드"),
    "object_trust": (r"\binvestment trusts?\b", r"투자신탁|신탁"),
    "object_bill": (r"\bclarity act\b", r"\bmarket structure bill\b", r"시장구조법안|클래리티법안?"),
    "object_stablecoin_bill": (r"\bgenius act\b", r"지니어스법안"),
    "object_patent": (r"\bpatent\b", r"특허"),
    "object_wallet": (r"\bwallet\b", r"지갑"),
    "object_commissioner": (r"\bcommissioner\b", r"위원|위원장"),
    "object_payment": (r"\bpayment infrastructure\b", r"\bpayment\b", r"결제\s*인프라|결제"),
    "object_custody": (r"\bcustod(?:y|ial)\b", r"수탁"),
    "object_lending": (r"\blending\b", r"\bloan\b", r"대출"),
    "object_fund": (r"\bfund\b", r"펀드"),
    "object_disclosure": (r"\bdisclosure\b", r"공개|공시"),
    "object_account": (r"\baccount\b", r"계정"),
    "object_card": (r"(?<![a-z])card(?!ano)", r"카드"),
    "object_bond": (r"\bbond\b", r"채권"),
    "object_license": (r"\blicen[cs]e\b", r"인가|라이선스"),
    "object_sanctions": (r"\bsanction(?:s|ed)?\b", r"제재"),
    "object_recovery": (r"\brecovery\b", r"복구"),
    "object_sale": (r"\bsell\b", r"\bsold\b", r"\bsale\b", r"매도|매각|처분|유출"),
    "object_board": (r"\bboard\b", r"\bfoundation member\b", r"이사회|재단\s*구성원"),
    "object_infrastructure": (r"\binfrastructure\b", r"인프라"),
    "object_regulated_trading_infrastructure": (
        r"\bregulated\s+(?:crypto|cryptocurrency|digital asset)\s+trading\s+infrastructure\b",
        r"\b(?:crypto|cryptocurrency|digital asset)\s+trading\s+infrastructure\b",
        r"\bregulated\s+(?:crypto|digital asset)\s+trading\s+(?:system|platform)\b",
        r"(?:규제(?:된|형)?\s*)?(?:암호화폐|가상자산|디지털자산)\s*거래\s*인프라",
        r"규제(?:된|형)?\s*(?:암호화폐|가상자산|디지털자산)\s*거래\s*(?:시스템|플랫폼)",
    ),
    "object_platform": (
        r"\b(?:trading|exchange)\s+platform\b",
        r"\bcrypto exchange\b",
        r"거래\s*플랫폼|암호화폐\s*거래소",
    ),
    "object_shutdown": (
        r"\b(?:shutdown|closure|service termination)\b",
        r"\bshut(?:s|ting)?\s+down\b.{0,30}\b(?:service|network|operations)\b",
        r"\bend(?:s|ed|ing)?\s+(?:service|network|operations)\b",
        r"폐쇄|운영\s*종료|영구\s*종료|서비스\s*종료|네트워크\s*종료",
    ),
    "object_class_action": (r"\bclass action\b", r"\blawsuit\b", r"집단\s*소송"),
    "object_insurance_fund": (r"\binsurance fund\b", r"보험\s*기금"),
    "object_bankruptcy": (
        r"\bchapter\s*11\b",
        r"\bbankruptcy(?:\s+protection)?\b",
        r"챕터\s*11|파산\s*보호|파산\s*절차|파산\s*신청",
    ),
    "object_asset_auction": (r"\basset\s+(?:sale|auction)\b", r"자산\s*(?:매각|경매)"),
    "object_derivatives": (r"\bderivatives?\b", r"파생상품"),
    "object_insider_desk": (
        r"\b(?:secret|insider|internal)\s+(?:trading\s+)?desk\b",
        r"비밀\s*내부자\s*거래\s*데스크|내부자\s*거래\s*데스크",
    ),
    "object_grant_report": (
        r"\b(?:grant|grant-backed|dev3pack)\b.{0,50}\b(?:final\s+)?report\b",
        r"\bdev3pack\b",
        r"보조금.{0,35}(?:최종\s*)?보고서|Dev3pack",
    ),
    "object_incubator": (r"\bincubator\b", r"인큐베이터"),
    "object_network": (r"\bnetwork\b", r"네트워크"),
    "object_hot_wallet": (r"\bhot\s*wallet\b", r"핫월렛|핫\s*월렛"),
    "object_etf_holdings": (
        r"\betf\b.{0,55}\b(?:holding|holdings|shares?|stake)\b",
        r"\b(?:holding|holdings|shares?|stake)\b.{0,55}\betf\b",
        r"ETF.{0,35}(?:보유|주식|지분)|(?:보유|주식|지분).{0,35}ETF",
    ),
    "object_rlusd": (r"\brlusd\b",),
    "object_adviser": (
        r"\b(?:senior\s+)?advis[eo]r\b",
        r"\badvisory\s+(?:role|post|position)\b",
        r"고문|자문역|정책\s*자문",
    ),
}

GEO_PATTERNS = {
    "geo_us": (r"\bunited states\b", r"(?<![a-z])u\.?s\.?(?![a-z])", r"\busa\b", r"미국"),
    "geo_korea": (r"\bsouth korea\b", r"(?<![a-z])korea(?![a-z])", r"한국"),
    "geo_japan": (r"\bjapan(?:ese)?\b", r"일본"),
    "geo_russia": (r"\brussia(?:n)?\b", r"러시아"),
    "geo_eu": (r"\beuropean union\b", r"(?<![a-z])eu(?![a-z])", r"유럽연합"),
    "geo_uk": (r"\bunited kingdom\b", r"(?<![a-z])uk(?![a-z])", r"\bbritain\b", r"영국"),
    "geo_india": (r"\bindia(?:n)?\b", r"인도"),
    "geo_bhutan": (r"\bbhutan\b", r"부탄"),
    "geo_hongkong": (r"\bhong kong\b", r"홍콩"),
    "geo_malaysia": (r"\bmalaysia(?:n)?\b", r"말레이시아"),
}

ASSET_PATTERNS = {
    "asset_btc": (r"(?<![a-z0-9])btc(?![a-z0-9])", r"\bbitcoin\b", r"비트코인"),
    "asset_eth": (r"(?<![a-z0-9])eth(?![a-z0-9])", r"\bethereum\b", r"이더리움"),
    "asset_xrp": (r"(?<![a-z0-9])xrp(?![a-z0-9])",),
    "asset_xrpl": (r"(?<![a-z0-9])xrpl(?![a-z0-9])", r"\bxrp ledger\b"),
    "asset_stablecoin": (r"\bstablecoin\b", r"스테이블코인"),
    "asset_usdt": (r"(?<![a-z0-9])usdt(?![a-z0-9])",),
    "asset_usdc": (r"(?<![a-z0-9])usdc(?![a-z0-9])",),
    "asset_rlusd": (r"(?<![a-z0-9])rlusd(?![a-z0-9])",),
    "asset_sol": (r"(?<![a-z0-9])sol(?![a-z0-9])", r"\bsolana\b", r"솔라나"),
}

SOURCE_NOISE = {
    "crypto", "bitcoin", "ethereum", "xrp", "news", "today", "latest", "update",
    "report", "analysis", "cointelegraph", "coindesk", "cryptopolitan",
    "cryptobriefing", "cryptopotato", "utoday", "thecryptobasic",
}

GENERIC_DUPLICATE_TOKENS = {
    "asset_btc", "asset_eth", "asset_xrp", "asset_xrpl", "asset_stablecoin",
    "action_launch", "action_partner", "action_invest", "action_disclose",
    "geo_us",
}

PARTICLES = (
    "에서는", "으로는", "에게는", "에서의", "으로", "에게", "에는", "에도", "에서",
    "은", "는", "인", "이", "가", "을", "를", "와", "과", "도", "만", "에", "로", "의",
)


def _story_text(story: dict) -> str:
    # Source domains such as crypto.news are not article evidence. Including
    # the URL here allowed unrelated AI and business stories to pass merely
    # because the publisher's domain contained the word "crypto".
    return "\n".join(
        str(story.get(key, "") or "")
        for key in ("title", "desc", "summary")
    )


def _matches(text: str, patterns: Iterable[str]) -> bool:
    return any(re.search(pattern, text or "", re.I) for pattern in patterns)


def _contains_alias(text: str, alias: str) -> bool:
    if not alias:
        return False
    escaped = re.escape(alias)
    if re.fullmatch(r"[A-Za-z0-9 .&'-]+", alias):
        escaped = escaped.replace(r"\ ", r"\s+")
        return bool(re.search(rf"(?<![A-Za-z0-9]){escaped}(?![A-Za-z0-9])", text, re.I))
    return alias in text


def _normalize_title(text: str) -> str:
    text = html.unescape(text or "").lower()
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"[^a-z0-9가-힣\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _has_crypto_core(text: str) -> bool:
    return _matches(text, CRYPTO_CORE_PATTERNS)


def target_assets(text: str) -> set[str]:
    return {
        symbol
        for symbol, patterns in TARGET_ASSET_PATTERNS.items()
        if _matches(text, patterns)
    }


def story_hash(title: str) -> str:
    """Return a stable Unicode-aware key for exact-title state tracking.

    The legacy hash removed every non-ASCII character.  Consequently most
    Korean titles hashed from an empty string and overwrote one another in
    ``news_state.json``, allowing older articles to be posted again.
    """

    normalized = html.unescape(title or "").casefold()
    normalized = re.sub(r"https?://\S+", " ", normalized)
    normalized = re.sub(r"[^a-z0-9가-힣]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def _is_hard_blocked(story: dict) -> tuple[bool, str]:
    raw = _story_text(story)
    title = str(story.get("title", "") or "")
    if _matches(raw, EXCLUDED_MARKET_CONTENT_PATTERNS):
        return True, "옵션·심리지수·추세·위믹스"
    if _matches(raw, HARD_BLOCK_PATTERNS):
        return True, "가격/전망/홍보/모음기사"
    if _matches(raw, LOW_VALUE_FLOW_PATTERNS):
        return True, "ETF·시장 단순 수급/주간 마감"

    aggregate_security_report = (
        _matches(
            raw,
            (
                r"\b(?:security|scam|phishing|fraud|social engineering)\b",
                r"보안\s*사고|피싱|사기|사회공학",
            ),
        )
        and _matches(
            raw,
            (
                r"\b(?:first half|second half|h1|h2|annual|quarterly|survey|statistics)\b",
                r"\b(?:multiple|dozens of|hundreds of)\s+incidents?\b",
                r"상반기|하반기|연간|분기|다수\s*사고|사고\s*\d+\s*건|집계|통계",
            ),
        )
        and _matches(
            raw,
            (
                r"\b(?:loss|losses|lost|incident|incidents|damage)\b",
                r"피해|손실|사고",
            ),
        )
        and not _matches(
            raw,
            (
                r"\b(?:arrested|charged|recovered|seized|indicted)\b",
                r"체포|기소|회수|압수",
            ),
        )
    )
    if aggregate_security_report:
        return True, "일반 보안·사기 피해 집계"

    kazakhstan_mining_power = (
        _matches(raw, (r"\bkazakhstan\b", r"카자흐스탄"))
        and _matches(
            raw,
            (
                r"\b(?:crypto|bitcoin|btc)?\s*(?:miner|mining)\b",
                r"암호화폐\s*채굴|비트코인\s*채굴|채굴업체",
            ),
        )
        and _matches(
            raw,
            (
                r"\b(?:electricity|power|energy|tariff|fee|rate)s?\b",
                r"전기\s*요금|전력\s*요금|전기료|전력",
            ),
        )
    )
    if kazakhstan_mining_power:
        return True, "포트폴리오 외 채굴 전기요금"

    is_clarity = _matches(
        raw,
        (
            r"\bclarity act\b",
            r"\bmarket structure bill\b",
            r"시장\s*구조\s*법안|시장구조법안|클래리티법안?",
        ),
    )
    clarity_commentary = _matches(
        raw,
        (
            r"\b(?:support|back|endorse|urge|press|push|call for|hope for|advocate)\w*\b",
            r"\b(?:still hope|needs support|should pass|must pass)\b",
            r"\b(?:seek|secure|round up|win|needs?)\s+(?:senate\s+|house\s+|enough\s+)?votes?\b",
            r"\b(?:urge|press|push|call on)\b.{0,45}\b(?:vote|amend|revise|change)\b",
            r"지지|촉구|압박|희망|통과해야|통과 필요|표\s*확보|의견\s*수용",
        ),
    )
    clarity_progress = _matches(
        raw,
        (
            r"\bvoted\b",
            r"\bvoting\s+(?:began|opened|started|scheduled)\b",
            r"\bvote\s+(?:scheduled|set|held|completed|passed|failed)\b",
            r"\b(?:scheduled|set)\b.{0,35}\bvote\b",
            r"\b(?:passed|passes|cleared|advanced|approved)\b",
            r"\b(?:amendment|revision)\s+(?:filed|introduced|approved|passed|adopted)\b",
            r"\b(?:bill|act)\s+(?:was\s+)?(?:amended|revised)\b",
            r"\b(?:hearing|markup|floor vote|committee vote)\b",
            r"\b(?:schedule|scheduled|reschedule|rescheduled|deadline|calendar)\w*\b",
            r"표결\s*(?:실시|시작|완료|예정|일정)|가결|통과(?:함|됨|됐다|돼)|"
            r"승인(?:함|됨|됐다|돼)|(?:수정안|개정안)\s*(?:제출|공개|통과|채택)|"
            r"심사\s*일정|본회의\s*(?:상정|통과|일정)|(?:상원|하원|위원회)\s*통과",
        ),
    )
    if is_clarity and clarity_commentary and not clarity_progress:
        return True, "클래리티법안 단순 지지·촉구"

    # A percentage in a concrete filing or investment is allowed.  A headline
    # whose main event is only price movement is not.
    market_move = _matches(
        title,
        (
            r"\b(?:price|token|coin|bitcoin|ethereum|xrp|btc|eth)\b.{0,40}"
            r"\b(?:rise|rises|rose|fall|falls|fell|drop|drops|dropped|surge|surges|jump|jumps|slide|slides)\b",
            r"\b(?:rise|rises|rose|fall|falls|fell|drop|drops|dropped|surge|surges|jump|jumps|slide|slides)\b"
            r".{0,40}\b(?:price|token|coin|bitcoin|ethereum|xrp|btc|eth)\b",
            r"가격.{0,25}(?:상승|하락|급등|급락)",
        ),
    )
    if market_move and not _matches(title, CONCRETE_EVENT_PATTERNS):
        return True, "단순 가격변동"

    if not target_assets(raw):
        return True, "지정 코인 핵심맥락 없음"

    return False, ""


def matches_keywords(
    story: dict,
    coins: list[str],
    econ_keywords: list[str],
    korean_keywords: list[str],
) -> bool:
    blocked, reason = _is_hard_blocked(story)
    if blocked:
        print(f"[편집필터 제외:{reason}] {story.get('title', '')}")
        return False

    raw = _story_text(story)
    if _matches(raw, CONCRETE_EVENT_PATTERNS):
        print(f"[구체사건 통과] {story.get('title', '')}")
        return True

    # A crypto keyword alone is insufficient.  This final positive gate keeps
    # market metrics, vague narratives, and commentary from being revived by
    # older permissive rules.
    print(f"[구체사건 없음 제외] {story.get('title', '')}")
    return False


def _collect_pattern_tokens(raw: str, table: dict[str, tuple[str, ...]]) -> set[str]:
    return {key for key, patterns in table.items() if _matches(raw, patterns)}


def _manual_translation_map() -> dict:
    mapping = _RUNTIME.get("MANUAL_TRANSLATIONS", {})
    return mapping if isinstance(mapping, dict) else {}


def _normalized_entity_token(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9가-힣]+", "", value or "").lower()
    return value[:40]


def _known_entity_tokens(raw: str) -> set[str]:
    tokens = set()
    for spec in ENTITY_SPECS:
        if spec.kind not in {"org", "person"}:
            continue
        if any(_contains_alias(raw, alias) for alias in spec.aliases):
            tokens.add(f"entity_{_normalized_entity_token(spec.label)}")
    return tokens


def _proper_entity_tokens(title: str) -> set[str]:
    tokens = set()
    translations = _manual_translation_map()
    candidates = re.findall(
        r"\b[A-Z][A-Za-z0-9&.'-]*(?:\s+[A-Z][A-Za-z0-9&.'-]*){0,3}\b",
        title or "",
    )
    for candidate in candidates:
        cleaned = candidate.strip(" .,'")
        low = cleaned.lower()
        if not cleaned or low in SOURCE_NOISE:
            continue
        if len(cleaned) <= 2:
            continue
        if low in {
            "united states", "south korea", "european union", "japan", "japanese",
            "russia", "russian", "china", "chinese", "india", "indian",
            "united kingdom", "britain", "hong kong",
        }:
            continue
        translated = translations.get(cleaned)
        is_acronym = bool(re.fullmatch(r"[A-Z][A-Z0-9&.-]{2,10}", cleaned))
        has_org_suffix = bool(
            re.search(
                r"\b(?:Bank|Foundation|Labs?|Research|Capital|Holdings?|Group|Protocol|"
                r"Technologies|Exchange|Commission|Authority)\b",
                cleaned,
                re.I,
            )
        )
        if translated is None and not (is_acronym or has_org_suffix):
            continue
        translated = translated or cleaned
        token = _normalized_entity_token(str(translated))
        if token and token not in SOURCE_NOISE:
            tokens.add(f"entity_{token}")
    return tokens


def _amount_tokens(raw: str) -> set[str]:
    text = raw or ""
    low = text.lower()
    out: set[str] = set()

    def add_usd(value: float) -> None:
        if value >= 1:
            out.add(f"amount_usd_{int(round(value))}")

    units = {
        "billion": 1_000_000_000, "bn": 1_000_000_000, "b": 1_000_000_000,
        "million": 1_000_000, "mn": 1_000_000, "m": 1_000_000,
        "thousand": 1_000, "k": 1_000,
    }
    money_patterns = (
        r"\$\s*([\d,]+(?:\.\d+)?)\s*(billion|million|thousand|bn|mn|b|m|k)?\b",
        r"\b([\d,]+(?:\.\d+)?)\s*(billion|million|thousand|bn|mn|b|m|k)"
        r"\s*(?:usd|dollars?)\b",
    )
    for pattern in money_patterns:
        for match in re.finditer(pattern, low, re.I):
            number = float(match.group(1).replace(",", ""))
            add_usd(number * units.get((match.group(2) or "").lower(), 1))

    for match in re.finditer(
        r"(\d+(?:\.\d+)?)\s*억(?:\s*(\d+(?:\.\d+)?)\s*만)?\s*달러",
        text,
    ):
        value = float(match.group(1)) * 100_000_000
        if match.group(2):
            value += float(match.group(2)) * 10_000
        add_usd(value)
    for match in re.finditer(r"(\d+(?:\.\d+)?)\s*만\s*(\d{1,4})?\s*달러", text):
        value = float(match.group(1)) * 10_000
        if match.group(2):
            value += int(match.group(2))
        add_usd(value)

    for match in re.finditer(
        r"(\d[\d,]*(?:\.\d+)?)\s*(btc|eth|xrp|usdt|usdc|rlusd)\b",
        low,
        re.I,
    ):
        value = float(match.group(1).replace(",", ""))
        asset = match.group(2).lower()
        exact = int(round(value))
        out.add(f"amount_{asset}_{exact}")
        if value >= 1_000:
            out.add(f"amount_{asset}_approx_{int(round(value / 100) * 100)}")
        elif value >= 100:
            out.add(f"amount_{asset}_approx_{int(round(value / 10) * 10)}")

    for match in re.finditer(r"\b(\d[\d,]*)\s*(?:shares?|units?)\b", low):
        out.add(f"count_shares_{int(match.group(1).replace(',', ''))}")
    for match in re.finditer(r"(?:(\d+)\s*만)?\s*(\d{1,4})\s*주\b", text):
        value = int(match.group(2)) + (int(match.group(1) or 0) * 10_000)
        out.add(f"count_shares_{value}")

    count_patterns = (
        (r"\b([\d,]+)\s*developers?\b", "developers"),
        (r"\b([\d,]+)\s*teams?\b", "teams"),
        (r"개발자\s*([\d,]+)\s*명", "developers"),
        (r"([\d,]+)\s*개\s*팀", "teams"),
    )
    for pattern, label in count_patterns:
        for match in re.finditer(pattern, text, re.I):
            out.add(f"count_{label}_{int(match.group(1).replace(',', ''))}")

    for match in re.finditer(r"\d+(?:\.\d+)?\s*%", low):
        value = match.group(0).replace(" ", "").replace("%", "")
        out.add(f"amount_pct_{value}")

    return set(sorted(out)[:12])


def _period_tokens(raw: str) -> set[str]:
    text = raw or ""
    out = set()
    for match in re.finditer(
        r"\b(20\d{2})\s*(?:q([1-4])|(?:first|second|third|fourth)\s+quarter|h([12])|"
        r"(?:first|second)\s+half)\b",
        text,
        re.I,
    ):
        value = match.group(0).lower()
        year = match.group(1)
        quarter_words = {"first": 1, "second": 2, "third": 3, "fourth": 4}
        if match.group(2):
            out.add(f"period_{year}_q{match.group(2)}")
        elif "quarter" in value:
            word = next((key for key in quarter_words if key in value), "")
            if word:
                out.add(f"period_{year}_q{quarter_words[word]}")
        elif match.group(3):
            out.add(f"period_{year}_h{match.group(3)}")
        elif "first half" in value:
            out.add(f"period_{year}_h1")
        elif "second half" in value:
            out.add(f"period_{year}_h2")
    for match in re.finditer(r"\b(20\d{2})년\s*([1-4])분기", text):
        out.add(f"period_{match.group(1)}_q{match.group(2)}")
    for match in re.finditer(r"\b(20\d{2})년\s*(상반기|하반기)", text):
        out.add(f"period_{match.group(1)}_{'h1' if match.group(2) == '상반기' else 'h2'}")
    return out


def _date_tokens(raw: str) -> set[str]:
    text = raw or ""
    out = set()
    month_names = {
        "jan": 1, "january": 1, "feb": 2, "february": 2,
        "mar": 3, "march": 3, "apr": 4, "april": 4,
        "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
        "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
        "oct": 10, "october": 10, "nov": 11, "november": 11,
        "dec": 12, "december": 12,
    }
    for match in re.finditer(
        r"\b(" + "|".join(month_names) + r")\.?\s+(\d{1,2})(?:st|nd|rd|th)?"
        r"(?:,|\s)\s*(20\d{2})\b",
        text,
        re.I,
    ):
        month = month_names[match.group(1).lower()]
        out.add(f"date_{match.group(3)}_{month:02d}_{int(match.group(2)):02d}")
    for match in re.finditer(r"\b(20\d{2})년\s*(\d{1,2})월\s*(\d{1,2})일", text):
        out.add(
            f"date_{match.group(1)}_{int(match.group(2)):02d}_{int(match.group(3)):02d}"
        )
    return out


def _event_tokens(story: dict) -> set[str]:
    raw = _story_text(story)
    title = str(story.get("title", "") or "")
    tokens = set()
    tokens |= _known_entity_tokens(raw)
    tokens |= _proper_entity_tokens(title)
    tokens |= _collect_pattern_tokens(raw, ACTION_PATTERNS)
    tokens |= _collect_pattern_tokens(raw, OBJECT_PATTERNS)
    tokens |= _collect_pattern_tokens(raw, GEO_PATTERNS)
    tokens |= _collect_pattern_tokens(raw, ASSET_PATTERNS)
    tokens |= _amount_tokens(raw)
    tokens |= _date_tokens(raw)
    tokens |= _period_tokens(raw)
    return tokens


def _signature_is_meaningful(tokens: set[str]) -> bool:
    non_assets = {token for token in tokens if not token.startswith("asset_")}
    has_entity = any(token.startswith("entity_") for token in tokens)
    has_action = any(token.startswith("action_") for token in tokens)
    has_object = any(token.startswith("object_") for token in tokens)
    # Asset-only combinations such as BTC|XRP must never be semantic duplicates.
    return len(non_assets) >= 2 and has_action and (has_entity or has_object)


def build_story_signature(story: dict) -> str:
    tokens = _event_tokens(story)
    if not _signature_is_meaningful(tokens):
        return ""
    return " | ".join(sorted(tokens))


def build_canonical_topic_key(story: dict) -> str:
    return build_story_signature(story)


def _split_signature(signature: str) -> set[str]:
    return {part.strip() for part in (signature or "").split("|") if part.strip()}


def _same_event(cur_signature: str, old_signature: str) -> bool:
    cur = _split_signature(cur_signature)
    old = _split_signature(old_signature)
    if not _signature_is_meaningful(cur) or not _signature_is_meaningful(old):
        return False

    shared = cur & old
    entities = {t for t in shared if t.startswith("entity_")}
    actions = {t for t in shared if t.startswith("action_")}
    objects = {t for t in shared if t.startswith("object_")}
    geos = {t for t in shared if t.startswith("geo_")}
    assets = {t for t in shared if t.startswith("asset_")}
    amounts = {t for t in shared if t.startswith("amount_")}
    dates = {t for t in shared if t.startswith("date_")}
    periods = {t for t in shared if t.startswith("period_")}

    # A named company's shutdown is one event even when one source focuses on
    # withdrawals and another on the insurance fund or related class action.
    cur_actions = {t for t in cur if t.startswith("action_")}
    old_actions = {t for t in old if t.startswith("action_")}
    closure_objects = {"object_shutdown", "object_platform"}
    if (
        entities
        and "action_close" in cur_actions
        and "action_close" in old_actions
        and closure_objects & cur
        and closure_objects & old
        and (dates or "object_shutdown" in (cur & old))
    ):
        return True

    specific_objects = {
        "object_bankruptcy",
        "object_class_action",
        "object_shutdown",
        "object_grant_report",
        "object_hot_wallet",
        "object_rlusd",
        "object_adviser",
        "object_insider_desk",
        "object_patent",
        "object_regulated_trading_infrastructure",
    }
    if entities and actions and objects & specific_objects:
        return True

    if (
        entities
        and actions
        and "object_etf_holdings" in objects
        and (assets or amounts or periods)
    ):
        return True

    if (
        entities
        and "action_invest" in actions
        and objects
        and (amounts or len(entities) >= 2)
    ):
        return True

    # The stable core is subject + action + object.  Region, amount, or asset
    # provides extra confidence when only one subject is shared. Two distinct
    # boosters are required for generic objects to avoid merging unrelated
    # launches or disclosures by the same company.
    boosters = sum(bool(group) for group in (geos, assets, amounts, dates, periods))
    if entities and actions and objects and (boosters >= 2 or len(entities) >= 2):
        return True
    if len(entities) >= 2 and objects and (actions or geos or amounts or periods):
        return True
    # Public-policy stories may name a regulator differently across sources.
    if actions and objects and geos and (amounts or assets):
        return True
    if actions and objects and len(geos) >= 2:
        return True
    return False


def is_canonical_duplicate(canonical_key: str, seen_keys: set[str]) -> bool:
    if not canonical_key:
        return False
    for old_key in seen_keys:
        if _same_event(canonical_key, old_key):
            _log(f"[사건중복 제외] {canonical_key} <> {old_key}")
            return True
    return False


def _title_words(title: str) -> set[str]:
    return {
        word
        for word in _normalize_title(title).split()
        if len(word) >= 3 and word not in SOURCE_NOISE
    }


def is_semantically_duplicate(
    story: dict,
    seen_signatures: list[str],
    seen_titles: list[str],
) -> bool:
    title = _normalize_title(str(story.get("title", "") or ""))
    words = _title_words(title)
    signature = build_story_signature(story)
    for old_title in seen_titles:
        old = _normalize_title(old_title)
        if title and old and SequenceMatcher(None, title, old).ratio() >= 0.91:
            _log(f"[제목중복 제외] {title} <> {old}")
            return True
        old_words = _title_words(old)
        if words and old_words:
            shared = words & old_words
            union = words | old_words
            if len(shared) >= 5 and len(shared) / max(1, len(union)) >= 0.64:
                _log(f"[제목사건중복 제외] shared={shared}")
                return True
        if signature:
            old_signature = build_story_signature({"title": old_title})
            if old_signature and _same_event(signature, old_signature):
                _log(f"[과거제목 의미중복 제외] {signature} <> {old_signature}")
                return True

    if not signature:
        return False
    for old_signature in seen_signatures:
        if _same_event(signature, old_signature):
            _log(f"[의미중복 제외] {signature} <> {old_signature}")
            return True
    return False


def _log(message: str) -> None:
    logger = _RUNTIME.get("log")
    if callable(logger):
        logger(message)
    else:
        print(message, flush=True)


def _summary_prompt(title: str, source_text: str) -> str:
    return f"""
너는 텔레그램 암호화폐 뉴스 채널 도리뉴스의 한국어 편집자다.

다음 기사를 짧고 또렷한 한국어 뉴스로 다시 써라.

필수 규칙:
- 기본은 2문장, 70~150자
- 첫 문장에 핵심 주체·행동·대상을 바로 제시
- 둘째 문장에는 핵심 수치·결과·의미 중 가장 중요한 것 하나만 제시
- 정보가 하나뿐이면 1문장으로 끝내도 됨
- 법률·소송·기술 제안처럼 사실이 3개 이상일 때만 '핵심 문장 + 불릿 2~3개' 허용
- 모든 문장을 완결하고 결론을 뒤로 미루지 말 것
- 문장마다 빈 줄 하나로 구분
- 문장 끝은 밝힘, 전함, 설명함, 추진함, 합류함, 승인함, 통과함, 공개함 등 축약형 사용
- 과장, 직역투, 추측, 전망, 홍보 문구 금지
- 매체명, 출처성 문구, '에 따르면', '이번 소식은' 삭제
- 기사에 없는 사실은 추가 금지
- 본문에는 해시태그를 쓰지 말 것
- 국가·기업·기관·인물은 가능한 한 통용되는 한국어 이름으로 표기
- XRP, XRPL, BTC, ETH, ETF, SEC, CFTC, IMF, IPO, AI 같은 약어는 원형 유지
- X 플랫폼과 X 계정은 '엑스'가 아니라 X로 표기
- milestone은 TON과 무관하므로 톤으로 번역하거나 태그하지 말 것
- 금/은은 영어 원문에서 Gold/Silver 귀금속 문맥일 때만 사용
- 마침표 없이 요약문만 출력

제목:
{title}

기사:
{source_text[:9000]}
""".strip()


def _compress_prompt(text: str) -> str:
    return f"""
아래 한국어 뉴스 요약을 사실을 바꾸지 말고 70~150자로 줄여라.
핵심 사건을 첫 문장에 두고 최대 2문장으로 완결하라.
불필요한 배경과 출처 표현을 삭제하라.
문장 끝은 밝힘, 전함, 설명함, 추진함, 승인함 같은 축약형으로 쓴다.
해시태그와 마침표는 쓰지 말고 요약문만 출력한다.

{text}
""".strip()


def _call_openai(prompt: str) -> str:
    client = _RUNTIME.get("openai_client")
    model = _RUNTIME.get("OPENAI_MODEL")
    if not client or not model:
        return ""
    try:
        response = client.responses.create(model=model, input=prompt)
        return str(getattr(response, "output_text", "") or "").strip()
    except Exception as exc:
        _log(f"[도리뉴스 편집 요약 실패] {exc}")
        return ""


def _remove_model_tags(text: str) -> str:
    # The editor owns tags.  Removing model tags prevents particles from being
    # fused before deterministic insertion.
    return re.sub(r"#([A-Za-z0-9가-힣_]+)", r"\1", text or "")


def _fix_style_endings(text: str) -> str:
    replacements = (
        (r"밝혔습니다$", "밝힘"),
        (r"밝혔다$", "밝힘"),
        (r"전했습니다$", "전함"),
        (r"전했다$", "전함"),
        (r"설명했습니다$", "설명함"),
        (r"설명했다$", "설명함"),
        (r"발표했습니다$", "발표함"),
        (r"발표했다$", "발표함"),
        (r"공개했습니다$", "공개함"),
        (r"공개했다$", "공개함"),
        (r"추진했습니다$", "추진함"),
        (r"추진했다$", "추진함"),
        (r"승인했습니다$", "승인함"),
        (r"승인했다$", "승인함"),
        (r"통과했습니다$", "통과함"),
        (r"통과했다$", "통과함"),
        (r"합류했습니다$", "합류함"),
        (r"합류했다$", "합류함"),
        (r"체포했습니다$", "체포함"),
        (r"체포했다$", "체포함"),
        (r"복구했습니다$", "복구함"),
        (r"복구했다$", "복구함"),
    )
    result = text.strip()
    result = re.sub(r"[.!。]+$", "", result)
    for pattern, replacement in replacements:
        result = re.sub(pattern, replacement, result)
    return result


def _clean_summary(text: str) -> str:
    text = html.unescape(text or "")
    text = _remove_model_tags(text)
    text = re.sub(r"(?im)^\s*(?:요약|제목|출처)\s*[:：]\s*", "", text)
    text = re.sub(r"(?i)\b(?:first appeared on|sponsored by)\b.*$", "", text)
    text = text.replace("가상자산", "암호화폐")
    text = re.sub(r"\b엑스(?=\s*(?:계정|게시물|플랫폼|에서|에|의))", "X", text)
    text = re.sub(r"(?i)\bmilestone\b", "마일스톤", text)
    text = text.replace("톤 마일스톤", "마일스톤")
    text = text.replace("있음고", "있다고").replace("했음고", "했다고")
    text = re.sub(r"자금\s*세탁", "자금 세탁", text)
    text = re.sub(r"은행\s*계좌", "은행 계좌", text)
    text = re.sub(r"페이퍼\s*컴퍼니", "페이퍼 컴퍼니", text)
    text = re.sub(r"하왈라\s*자금", "하왈라 자금", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    paragraphs = []
    for paragraph in text.split("\n\n"):
        lines = []
        for line in paragraph.splitlines():
            line = line.strip()
            if not line:
                continue
            bullet = ""
            if re.match(r"^[•●▪\-]\s*", line):
                bullet = "• "
                line = re.sub(r"^[•●▪\-]\s*", "", line)
            line = _fix_style_endings(line)
            if line:
                lines.append(bullet + line)
        if lines:
            paragraphs.append("\n".join(lines))

    # Keep two normal paragraphs.  For a genuine list keep one lead plus up to
    # three bullets.
    has_bullets = any(line.startswith("• ") for p in paragraphs for line in p.splitlines())
    if has_bullets:
        flat = [line for p in paragraphs for line in p.splitlines() if line.strip()]
        lead = [line for line in flat if not line.startswith("• ")][:1]
        bullets = [line for line in flat if line.startswith("• ")][:3]
        return "\n\n".join(lead + bullets).strip()
    return "\n\n".join(paragraphs[:2]).strip()


def format_summary_for_telegram(
    text: str,
    max_sentences: int = 2,
    max_chars: int = TARGET_SUMMARY_CHARS,
) -> str:
    # Never slice by character count: an overlong but complete sentence is
    # safer than a short, broken sentence.
    summary = _clean_summary(text)
    paragraphs = [p.strip() for p in summary.split("\n\n") if p.strip()]
    return "\n\n".join(paragraphs[: max(1, min(max_sentences, 3))])


def _dynamic_specs(raw: str) -> list[EntitySpec]:
    specs = []
    mapping = _manual_translation_map()
    for alias, translated in sorted(mapping.items(), key=lambda item: len(str(item[0])), reverse=True):
        alias = str(alias or "").strip()
        translated = str(translated or "").strip()
        if not alias or not translated or len(translated) > 24:
            continue
        if " " in translated or translated in {"암호화폐", "금융", "시장", "규제", "자산", "법안"}:
            continue
        if not _contains_alias(raw, alias):
            continue
        footer = ""
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9 .&'-]+", alias):
            footer_name = re.sub(r"[^A-Za-z0-9]", "", alias)
            if 2 < len(footer_name) <= 28:
                footer = "#" + footer_name
        specs.append(EntitySpec("dynamic", translated, (alias, translated), footer, 28))
        if len(specs) >= 12:
            break
    return specs


def _surface_pattern(surface: str) -> str:
    escaped = re.escape(surface)
    if re.fullmatch(r"[A-Za-z0-9 .&'-]+", surface):
        escaped = escaped.replace(r"\ ", r"\s+")
        return rf"(?<![A-Za-z0-9#]){escaped}(?![A-Za-z0-9_])"

    particle_pattern = "|".join(re.escape(p) for p in PARTICLES)
    return (
        rf"(?<![#A-Za-z0-9가-힣]){escaped}"
        rf"(?=(?:{particle_pattern})(?=[^A-Za-z0-9가-힣_]|$)|[^A-Za-z0-9가-힣_]|$)"
    )


def _hashed_surface_pattern(surface: str) -> str:
    escaped = re.escape(surface)
    if re.fullmatch(r"[A-Za-z0-9 .&'-]+", surface):
        escaped = escaped.replace(r"\ ", r"\s+")
        return rf"(?<![A-Za-z0-9_])#{escaped}(?![A-Za-z0-9_])"

    particle_pattern = "|".join(re.escape(p) for p in PARTICLES)
    return (
        rf"(?<![A-Za-z0-9가-힣_])#{escaped}"
        rf"(?=(?:{particle_pattern})(?=[^A-Za-z0-9가-힣_]|$)|[^A-Za-z0-9가-힣_]|$)"
    )


def _first_surface_match(text: str, spec: EntitySpec):
    matches = []
    for surface in set((spec.label,) + spec.aliases):
        match = re.search(_surface_pattern(surface), text, re.I)
        if match:
            matches.append((match.start(), -len(match.group(0)), match, surface))
    return min(matches, key=lambda item: (item[0], item[1])) if matches else None


def _candidate_specs(summary: str, story: dict) -> list[EntitySpec]:
    raw = _story_text(story)
    title = str(story.get("title", "") or "")
    candidates = []
    seen = set()
    for spec in ENTITY_SPECS + tuple(_dynamic_specs(raw)):
        if spec.label in seen:
            continue
        in_raw = any(_contains_alias(raw, alias) for alias in spec.aliases)
        in_summary = spec.label in summary or any(_contains_alias(summary, alias) for alias in spec.aliases)
        if not (in_raw or in_summary):
            continue
        # Gold/Silver are intentionally not entity specs.  TON is exact only.
        title_hit = any(_contains_alias(title, alias) for alias in spec.aliases)
        rank = spec.priority - (5 if title_hit else 0)
        first_match = _first_surface_match(summary, spec)
        first_position = first_match[0] if first_match else len(summary) + 1
        candidates.append((first_position, rank, spec))
        seen.add(spec.label)
    candidates.sort(key=lambda item: (item[0], item[1]))
    return [spec for _, _, spec in candidates]


def _replace_surface_with_tag(text: str, spec: EntitySpec) -> tuple[str, bool]:
    tag = f"#{spec.label}"
    surfaces = tuple(dict.fromkeys((spec.label,) + spec.aliases))

    # Remove model-provided or previously inserted tags for this entity first.
    # The deterministic pass below then tags only the earliest occurrence.
    for surface in sorted(surfaces, key=len, reverse=True):
        text = re.sub(_hashed_surface_pattern(surface), surface, text, flags=re.I)

    first = _first_surface_match(text, spec)
    if not first:
        return text, False
    _, _, match, _ = first
    return text[: match.start()] + tag + text[match.end() :], True


def _is_clarity_story(story: dict) -> bool:
    return _matches(
        _story_text(story),
        (
            r"\bclarity(?:\s+act)?\b",
            r"\bmarket structure bill\b",
            r"시장\s*구조\s*법안|시장구조법안|클래리티법안?",
        ),
    )


def _normalize_clarity_text(text: str, clarity_context: bool = False) -> str:
    text = re.sub(
        r"#?\b(?:CLARITY(?:\s+Act)?|Clarity\s+Act|market\s+structure\s+bill)\b",
        "클래리티법안",
        text,
        flags=re.I,
    )
    text = re.sub(
        r"#?(?:클래리티법안?|시장\s+구조\s+법안)",
        "클래리티법안",
        text,
    )
    if clarity_context:
        text = re.sub(
            r"(?<![가-힣])(?:명확성\s*)?#?법안",
            "클래리티법안",
            text,
        )
    return text


def fix_hashtag_particles(
    text: str,
    extra_known_tags: Iterable[str] = (),
) -> str:
    known_tags = {spec.label for spec in ENTITY_SPECS}
    known_tags.update(str(tag).lstrip("#") for tag in extra_known_tags if tag)
    particles = sorted(PARTICLES, key=len, reverse=True)

    def separate(match: re.Match) -> str:
        token = match.group(1)
        if token in known_tags:
            return f"#{token}"
        for particle in particles:
            if not token.endswith(particle):
                continue
            base = token[: -len(particle)]
            if base in known_tags:
                return f"#{base} {particle}"
        return f"#{token}"

    text = re.sub(r"#([A-Za-z0-9가-힣_]+)", separate, text)
    text = re.sub(r"(#[A-Za-z0-9가-힣_]+)\s+([,，])", r"\1\2", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def _inject_inline_tags(summary: str, story: dict) -> tuple[str, list[EntitySpec]]:
    selected = []
    tagged = _normalize_clarity_text(summary, clarity_context=_is_clarity_story(story))
    for spec in _candidate_specs(tagged, story):
        if len(selected) >= MAX_INLINE_TAGS:
            break
        tagged, replaced = _replace_surface_with_tag(tagged, spec)
        if replaced:
            selected.append(spec)

    tagged = fix_hashtag_particles(tagged, (spec.label for spec in selected))
    tagged = tagged.replace("#마이클 #세일러", "#마이클세일러")
    tagged = tagged.replace("#데이비드 #슈워츠", "#데이비드슈워츠")
    tagged = tagged.replace("#찰스 #호스킨슨", "#찰스호스킨슨")
    tagged = tagged.replace("#시장구조 #법안", "#클래리티법안")
    return tagged, selected


def _has_precious_metal_context(raw: str, metal: str) -> bool:
    if metal == "gold":
        return bool(re.search(r"\bgold\b", raw, re.I))
    return bool(re.search(r"\bsilver\b", raw, re.I))


def _build_footer_tags(story: dict, selected: list[EntitySpec]) -> list[str]:
    raw = _story_text(story)
    article_tags = []
    body_equivalent_tags = set()
    for spec in selected:
        body_equivalent_tags.add(f"#{spec.label}")
        if spec.footer:
            body_equivalent_tags.add(spec.footer)
        if spec.label == "비트코인":
            body_equivalent_tags.add("#BTC")

    if _is_clarity_story(story) and "#클래리티법안" not in body_equivalent_tags:
        article_tags.insert(0, "#클래리티법안")

    ticker_patterns = (
        ("#XRP", r"(?<![A-Za-z0-9])XRP(?![A-Za-z0-9])"),
        ("#XRPL", r"(?<![A-Za-z0-9])XRPL(?![A-Za-z0-9])|\bXRP Ledger\b"),
        ("#ETH", r"(?<![A-Za-z0-9])ETH(?![A-Za-z0-9])|\bEthereum\b"),
        ("#USDT", r"(?<![A-Za-z0-9])USDT(?![A-Za-z0-9])"),
        ("#USDC", r"(?<![A-Za-z0-9])USDC(?![A-Za-z0-9])"),
        ("#SOL", r"(?<![A-Za-z0-9])SOL(?![A-Za-z0-9])|\bSolana\b"),
        ("#ETF", r"(?<![A-Za-z0-9])ETF(?![A-Za-z0-9])"),
    )
    for tag, pattern in ticker_patterns:
        if (
            tag not in body_equivalent_tags
            and re.search(pattern, raw, re.I)
            and tag not in article_tags
        ):
            article_tags.append(tag)
        if len(article_tags) >= MAX_ARTICLE_TAGS:
            break

    if _has_precious_metal_context(raw, "gold") and "#Gold" not in article_tags:
        article_tags.append("#Gold")
    if _has_precious_metal_context(raw, "silver") and "#Silver" not in article_tags:
        article_tags.append("#Silver")

    clean = []
    for tag in article_tags[:MAX_ARTICLE_TAGS] + list(FIXED_FOOTER_TAGS):
        if tag and tag not in body_equivalent_tags and tag not in clean:
            clean.append(tag)
    return clean


def _rewrite_summary(story: dict) -> str:
    title = str(story.get("title", "") or "")
    desc = str(story.get("desc", "") or "")
    get_source = _RUNTIME.get("get_best_source_text")
    source_text = get_source(story) if callable(get_source) else desc or title
    source_text = str(source_text or desc or title)
    summary = _call_openai(_summary_prompt(title, source_text))
    summary = _clean_summary(summary)
    if len(re.sub(r"\s+", "", summary)) > HARD_SUMMARY_CHARS:
        shorter = _clean_summary(_call_openai(_compress_prompt(summary)))
        if shorter:
            summary = shorter
    return format_summary_for_telegram(summary, max_sentences=2, max_chars=TARGET_SUMMARY_CHARS)


def _summary_is_market_only(summary: str) -> bool:
    return _matches(summary, TECHNICAL_SUMMARY_PATTERNS) or _matches(
        summary,
        EXCLUDED_MARKET_CONTENT_PATTERNS,
    )


def build_message(story: dict) -> str:
    blocked, reason = _is_hard_blocked(story)
    if blocked:
        _log(f"[전송전 편집필터 제외:{reason}] {story.get('title', '')}")
        return ""

    summary = _rewrite_summary(story)
    if not summary:
        _log(f"[요약실패 스킵] {story.get('title', '')}")
        return ""
    if _summary_is_market_only(summary):
        _log(f"[전송전 지지선·시황 제외] {story.get('title', '')}")
        return ""

    refusal_check = _RUNTIME.get("is_refusal_or_skip_text")
    if callable(refusal_check) and refusal_check(summary):
        _log(f"[요약거부 스킵] {story.get('title', '')}")
        return ""

    summary, selected = _inject_inline_tags(summary, story)
    summary = fix_hashtag_particles(summary)
    footer_tags = _build_footer_tags(story, selected)

    url = html.escape(str(story.get("url", "") or ""), quote=True)
    parts = (
        html.escape(summary),
        '🌐 <a href="http://t.me/Doorinews">공식 글로벌 실시간 도리뉴스</a>',
        f'<a href="{url}">출처</a>',
        " ".join(html.escape(tag) for tag in footer_tags),
    )
    return "\n\n".join(parts)


def install_editor_overrides(runtime: dict) -> None:
    """Install one final, explicit editorial layer into ``doorinews_bot``."""

    global _RUNTIME, _PREVIOUS_MATCHES
    _RUNTIME = runtime
    _PREVIOUS_MATCHES = runtime.get("matches_keywords")

    runtime["matches_keywords"] = matches_keywords
    runtime["story_hash"] = story_hash
    runtime["build_story_signature"] = build_story_signature
    runtime["build_canonical_topic_key"] = build_canonical_topic_key
    runtime["is_canonical_duplicate"] = is_canonical_duplicate
    runtime["is_semantically_duplicate"] = is_semantically_duplicate
    runtime["format_summary_for_telegram"] = format_summary_for_telegram
    runtime["build_message"] = build_message
    runtime["DOORINEWS_EDITOR_VERSION"] = "2026-07-27-market-exclusions-v4"
    _log("[편집엔진] doorinews_editor 2026-07-27-market-exclusions-v4 적용")
