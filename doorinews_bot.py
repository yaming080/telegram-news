#!/usr/bin/env python3
import asyncio
import hashlib
import html
import json
import os
import re
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from html import unescape
from inspect import iscoroutine
from difflib import SequenceMatcher

from openai import OpenAI


TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "")
INITIAL_RUN = os.environ.get("INITIAL_RUN", "false").strip().lower() == "true"
POST_ENABLED = os.environ.get("POST_ENABLED", "true").strip().lower() == "true"
DRY_RUN_RECORD = os.environ.get("DRY_RUN_RECORD", "false").strip().lower() == "true"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.4-mini").strip() or "gpt-5.4-mini"
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

FEEDS = [
    ('Cointelegraph', 'https://cointelegraph.com/rss'),
    ('크립토폴리탄', 'https://www.cryptopolitan.com/feed/'),
    ('더크립토베이식', 'https://thecryptobasic.com/feed/'),
    ('토큰포스트', 'https://www.tokenpost.kr/rss'),
    ('비트코이니스트', 'https://bitcoinist.com/feed/'),
    ('코인에디션', 'https://coinedition.com/feed/'),
    ('크립토포테이토', 'https://cryptopotato.com/feed/'),
    ('더뉴스크립토', 'https://thenewscrypto.com/feed/'),
    ('유투데이', 'https://u.today/rss.php'),
    ('크립토뉴스닷뉴스', 'https://crypto.news/feed/'),
]


PORTFOLIO_COINS = ['BTC','ETH','XRP','XLM','ADA','TRX','BNB','BCH','SHIB','ETC','FLR','ATHENA','ENA','USDC','USDT']

OTHER_COINS = [
    'HYPE','HYPERLIQUID','SOL','DOGE','AVAX','DOT','MATIC','POL','LINK','LTC','ATOM',
    'ARB','OP','SUI','APT','PEPE','WIF','BONK','INJ','RNDR','NEAR',
    'FIL','HBAR','TIA','KAS','TAO','ICP','UNI','AAVE','MKR','TRUMP',
    'METAWIN','PI','WLD','RIVER','G COIN','PLAYNANCES','LDO', 'LIDO', 'AKT', 'AKASH', 'AKASH NETWORK'
]

ECON_KEYWORDS = ['sec','etf','regulation','law','bill','inflation','interest rate','economy','government','bank','approval','legislation','policy','tariff','Fed','korea','stablecoin','tokenization','custody','seed phrase','treasury','cftc','occ','ipo',
    'basel','basel iii','liquidity','hqla','odl','on-demand liquidity',
'hearing','senate','house','committee','license','margin','collateral','oil','crude','lng','sanction','tariff','tax','income tax','unemployment',
    'jobs','claims','fed','rate hike','treasury strategy','geopolitics','war','gold','digital gold','quantum','bip360','recovery trust','creditor','distribution',
    'ipo','lawsuit','treasury strategy','predictive market']

KOREAN_KEYWORDS = [
    '비트코인','이더리움','리플','스텔라','에이다','트론','바이낸스코인','비트코인캐시','시바이누','시바','스테이블코인','토큰화','수탁','시드문구',
    'ETF','현물 ETF','SEC','CFTC','OCC',
    '규제','법안','입법','정책','승인','소송',
    '연준','금리','금리인상','금리인하','인플레이션',
    '경제','정부','은행','국채','재무부',
    '관세','제재','유가','원유','LNG',
    '상원','하원','청문회','위원회',
    '한국','국내','브라질','중국','일본','미국','이란','이스라엘','카타르',
    '실업수당','고용','고용지표','기관','유동성','배당금','채권자',
    '양자','컴퓨팅','공격','방지','배포','금','디지털 금','세계금협회',
    '예측시장','차량공유','카풀','거래소','감독'
]
KOREAN_TAG_KEYWORDS = [
    '비트코인', '이더리움', '리플', '스텔라', '에이다', '트론',
'시바이누', '스테이블코인',
'미국', '이란', '이스라엘', '일본', '한국', '중국', '브라질',
'연준', '환율', '유동성', '재무부',
'ETF', 'SEC', 'CFTC', 'OCC', 'Polymarket', '폴리마켓',
'업비트', '빗썸', '바이낸스', '코인베이스',
'모건스탠리', '골드만삭스', '크라켄', '로빈후드',
'일론머스크', '갈링하우스', '제롬파월', '트럼프',
'아이언라이트', '보어히스', '에릭보어히스', '마이클세일러', '세일러', '로버트기요사키', '폴앳킨스',
'데이비드슈워츠', '마이크노보그라츠', '샘알트만', '셰이프시프트', '브래드갈링하우스', '모니카롱',
'비탈릭부텔린', '사토시나카모토', '저스틴썬', '제드맥케일럽', '찰스호스킨슨',
'스트래티지', '도널드트럼프', '테더', '플레어', 'FLR', '에테나', '에테나', '메타플래닛', '도리뉴스',
'시바리움', 'SWIFT', '백악관', '카타르', '마스터카드',
'IPO', 'CTO', 'XRP', 'XLM', 'BTC', 'ETH', 'SHIB', 'USDC', 'USDT', 'XAUT', 'SOL', 'DOGE',
    'RLUSD', 'FOMC', '헤스터피어스', '시카고상품거래소', '키발리스', '라울팔', '누바', '템포', '머니그램', '미카', '도호쿠은행', 'SBIRemit', '소프트뱅크', '트웬티원캐피털', '화이트비트', '티머시매사드', '무로', '산탄데르',
'토큰화', '수탁', '시드문구', '소송', '규제', '해석',
'DeFi', 'NFT', 'Web3', 'BitMine', '톰리', 'Thomasgeth', 'TimeTraveler', 'JohnSquire',
'유니스왑', 'HaydenAdams', '파월', 'America', '네비다주', 'JPMorgan', '라이드', '바이비트', 'Ledger',
'서클', '머니그램', 'Apple', '페이팔', '스트라이프', '제미니', '칼시', '제드시온', '에버노스',
'XRPLedger', '세계금협회', '디지털금', '비트코인퀀텀', 'BIP360', 'OpenAI', 'Anthropic',
'슈퍼마이크로', 'AI', 'LNG', '바잔', '캘리포니아', '지니어스법안', '지니어스', '법안', 'ICE',
'클래리티', '블랙록', '문페이', '히든로드', '게임스탑', '구글', '인도', '웰스파고', '피터쉬프', '패니매','ICE', 'EEZ', '현물', '서울', '부산',
	'휘발유', '경유', '대전', '인천', '대구','경기도', '울산', '강원도', '석유', '비트코인캐시','월스트리트',
	'매수', '기관자금', '디파이', '오픈크레딧', '스마트계약', '프라이빗크레딧','비트코인캐시', '노동부', '401k',
	'밈코인','레이어2','금융', '암호화폐', '트론', 'TRX', 'TRON', '호주', '미국',
'프랭클린템플턴', '토니피코어','위즈덤트리', '클래리티법','마이클바', 'Michael Barr',
'홍콩', 'Hong Kong', 'HKMA', '홍콩금융관리국',
'HSBC', '스탠다드차타드', 'Standard Chartered','Michael Selig', '마이클셀릭', '마이클 셀릭',
'GENIUS', 'Genius Act',
'수탁업체','Jack Dorsey', '잭도시', 'Block','Paul Grewal', '폴그루월', '그루월',
'Brad Garlinghouse', '브래드갈링하우스', 'CEO',
'Genius Group', '지니어스그룹',
'Government', '정부', 'KYC',
'FTX', 'Nishad Singh', '니샤드싱',
'KBank', '케이뱅크',
'eToro', 'Taiwan', '대만',
'Coinone', '코인원',
'Bitget', 'SafePal', '마이크로소프트', 'Microsoft','XRPL', 'DEX', '탈중앙거래소', '사토시쿠사마','Bitdeer', '비트디어','Blockstream', '블록스트림',
'IMF', '토비아스아드리안', 'Tobias Adrian', 'RWA', '지니어스법안','Charles Schwab', '찰스슈왑','Oracle', '오라클','Peter Schiff','피터쉬프','금융당국', '사모대출', '잉글랜드은행', '앤드루베일리',
'한국은행', '보험연수원', '디지털화폐', '디지털통화', '지수보험',
'일본은행', '유가', '국채', '신현송', 'CBDC',
'메타플래닛', '일본 정부', '코인원', '코인원 AML',
'ABA', '예금', '은행예금', '금융위원회',
'모니카롱', 'ODL', 'FedNow', 'Fedwire',
'금융상품거래법', '금융상품', '스테이블코인', '클래리티법안',
'브래드갈링하우스', '리플 CEO', '블랙록 CEO',
'SMQKE', '신탁은행', '마스터계정', '금융감독청',
'주택시장', '제프박', '프로캡',
'업비트', 'USDT', '원화마켓', 'KRW',



	
]

NEGATIVE_KEYWORDS = [
    'newsletter', 'the daily', '더데일리', '뉴스레터', '발췌', '발췌한 것임',
    '다음은', '게스트 게시물', '오늘의 토큰운세',
    '토큰운세', '띠별 토큰 운세',
    '투자참고용이 아닌',
    '심리적 환기와 재미를 위해',
    '투자 조언도 아님',
    '일일 동향 및 이벤트',
    '토큰포스트마켓에 따르면',
    '소식통에 따르면',
    '관계자에 따르면',
    '업계에 따르면',
    '시장에 따르면',
    '본 콘텐츠는 특정 종목이나 자산에 대한 투자 조언이 아니며',
    '변동성 높은 시장에서 흔들리지 않는 투자 마인드를 가꾸기 위한 심리적 환기 목적으로 제공됩니다',
    '심리적 환기 목적으로 제공됩니다',
    'daily events',
    'crypto today',
    'what happened in crypto today',
    'guest post', 'guest article', 'op-ed', 'analysis by',
    'daily update', 'economic update', 'market update',
    'how to build', 'platform infrastructure', 'investment platform',
    'price prediction', 'forecast', 'will it reach', 'can it reach',
    'presale', 'pre-sale', 'launch week', 'turns launch week',
    'pi network', 'g coin', 'playnances', 'metawin', 'river', 'wld', 'avax', 'solana', 'dogwifhat', 'wif',
    'hyperliquid', 'hype token', 'hype etf',
    'alex bores', 'sam bankman-fried', 'democratic primary',
    'first appeared on',
    '처음 게재되었',
    '처음 게재되었습니다',
    'times tabloid에 처음 게재', 'Times Tabloid 에 처음으로 게재되었음',
    'timestabloid에 처음 게재',
    'ATH 대비',
    '토큰포스트',
    '투자 심리',
    '본 콘텐츠는','과매수 신호가','과매도 신호','코인데스크에 따르면',
    'coindesk에 따르면',
    'cryptonews 에 처음 등장함',
    'cryptonews에 처음 등장함',
    'crypto biz:',
    'crypto biz',
    'coindesk according to',
    'cryptonews first appeared','CryptoBriefing','Crypto Briefing','Cointelegraph','CryptoSlate','TheBlock','WatcherGuru',
	'Cryptopolitan','처음으로 게재되었음','데드크로스','Death Cross',
    'TheCryptoBasic','CoinGape','TimesTabloid','DailyHodl','BeInCrypto','BloomingBit','NewsBitcoin','CoinTurk', '.com News',
	'코인 소식 중 중요한 내용만 PiCK 해서 보세요', '뉴스 속보를 제공해요','게시물임','청산','하락','급락','Crypto Briefing 에서',
	'황정수의 글로벌 체크인','defillama.com','하락함','청산됨','매도 압력', '이 작성함', '이재명','bristol myers squibb', 'bmy', 'biopharma', 'pharma', 'pharmaceutical',
'drug', 'therapy', 'treatment', 'clinical', 'trial', 'patient',
'medicine', 'healthcare', 'biotech', 'phase 1', 'phase 2', 'phase 3','제약', '바이오', '임상', '치료제', '약물', '환자',
	'의약품', '헬스케어','price drop', 'market drop', 'drops below', 'decline', 'declined','fell', 'fall below', 'slump',
	'sell-off', 'bearish','극단적인 공포','extreme fear','Conjecture', 'could impact bitcoin', 'could impact bitcoin',
'could affect bitcoin',
'how weakening us labor data',
'what this means',
'what it means',
'might impact bitcoin',
'may impact bitcoin',
'could affect bitcoin',
'how weakening us labor data',
'what this means',
'what it means',
'might impact bitcoin',
'may impact bitcoin',
	'first appeared on times tabloid',
    'appeared first on times tabloid',
    'first published on times tabloid',
    'published first on times tabloid',
    'first appeared on timestabloid',
    'appeared first on timestabloid',
    'first published on timestabloid',
    'published first on timestabloid',
    'morning crypto report',
'weak price action',
'rising leverage',
'unstable setup',
'가격조정', '가격 조정',
'레버리지','온톨로지','TxFlow','제트캐시', 'zcash','practical guide', 'practical guide to', 'guide to choosing', 'market maker guide',
'실용 가이드', '실용가이드','liquidates entire bitcoin stash',
'bitcoin stash',
'liquidate bitcoin holdings',
'liquidates holdings',
'debt repayment',
'repay debt',
'sell bitcoin to repay debt',
'전량 매각',
'비트코인 전량 매각',
'부채 상환 위해 매각',
'보유 비트코인 매각',

'lido dao', 'ldo', 'redemption', 'proposed sale', 'token sale',
'환매', '매각 제안',

'surge', 'spike', 'jumps', 'rally', 'best quarter', 'worst quarter', 'buying opportunity',
'급등', '상승폭', '최악', '분기', '매수 기회',

'metals.io', 'metals io', 'trillitech', 'trili tech',
'crypto tax', 'customers don’t understand crypto tax', 'customers do not understand crypto tax',
'암호화폐 세금', '고객의 절반 이상이 암호화폐 세금을 이해하지 못함',

'raised', 'raise', 'raising', 'funding', 'series a', 'fundraise', 'fundraising',
'모금', '모금함', '자금조달', '시리즈', 'critical thinking', '비판적 사고',
'blasts xrp community', '폭파함',
'breaks macro model', '다시 깨뜨립니다',
'payment cost', '지불 비용', '지불비용',
'bounce zone', '반등 구간', '반등구간',
'selling pressure', 'sell pressure', '매도세',
'kucoin',
'hashrate', '해시레이트',
'bleeding', '출혈',
'불안을 촉발함',
'fundraise', 'fundraising', '모금', '모금함', '자금조달',
'리스크 오프',
'test support', '지지선 시험대',
'entry zone', '진입 구역',
'monthly chart', '월간 차트','reason', 'reasons',
'uncertain', 'uncertainty', '불확실', '불확실성','reason', 'reasons', 'why', '이유', 'oil', 'solar', 'renewable', 'dividend', 'shareholder', 'board reshuffle',
'주주총회', '배당', '태양광', '에너지 전환', '중장기 성장 전략', 'game ai', 'gaming ai', 'game content', 'series b', 'funding round',
'게임 ai', '게임 콘텐츠', '시리즈 b', '펀딩', '마케팅 자산', '자동화 툴', 'BitGo', 'listing', 'listings', 'delisting', 'delist', 'delisted',
'상장', '상장 소식', '상장 발표', '상장 폐지', '폐지 결정', '거래지원 종료',
'binance listing', 'binance delisting', '바이낸스 상장', '바이낸스 상장 폐지','analyst',
'analysis',
'correlation',
's&p correlation',
'hack',
'hacker',
'scam',
'fraud',
'social engineering',
'charged',
'prison sentence',
'canton network',
'iboxx',
'us treasuries',
	    'green monthly candle',
    'red monthly streak',
    'monthly streak',
    'monthly candle',
    'fear and greed',
    'fear index',
    'bottom signal',
    'local bottom',
    'what’s next for april',
    "what's next for april",
    'what comes next',
    'holds $',
    'holds usd',
    'fails to break higher',
    'price fails to break higher',
    'barely avoids',
    'worst red monthly',
    'worst monthly streak',
    '극단적 공포',
    '공포탐욕지수',
    '바닥 신호',
    '월봉',
    '녹색 월간 양초',
    '적색 월간',
    '상승 마감','mercado coin','mercado libre',
'loyalty rewards',
'loyalty program',
'rewards program','market recovery',
'active xrp users',
'active users cross',
'threshold enabling',
'0 recorded in xrp etf investments',
'april fools joke',
'minus monthly close',
'negative monthly close',
'positive monthly close',
'monthly close',
'market recovery possible',
'retail users',
'trading assistant',
'ai trading assistant',
'mulerun',
'wcf',
'winklevoss capital fund',
'gemini ipo',
'ipo controversy',
'discounted shares','transaction fee',
'transaction fees',
'inscription',
'inscriptions',
'soft fork',
'block space',
'block size',
'throughput',
'트랜잭션 수수료',
'인스크립션',
'소프트포크', 'bollinger',
'bollinger bands',
'major move looms',
'major move',
'tightening',
'descending channel',
'golden cross',
'burn rate rockets',
'network activity',
'eastpoint',
'eastpoint seoul',
'co-hosted',
'hosted by',
'conference 2026',
'september 28',
'registration',
'networking event',
'공동 주최',
'주최',
'개최',
'행사 개최','what’s next',
"what's next",
'know this before you join them',
'tumbling',
'lower highs',
'price correction',
'risk-off approach',
'could rise to',
'could see further dips',
'rejection at the',
'resistance level',
'financial report',
'재무 요약',
'재무 보고서',
'총자산',
'런웨이',
'grant efficiency',
'운영비 효율성',

'miners continue selling',
'miner selling',
'채굴자들이 계속 판매',
'채굴자들이 계속 매도',
'sells 3778 btc',
'sells btc in q1',
'판매하며',
'매도 중임',
'매도 기사',

'liquidation imbalance',
'liquidations',
'청산 불균형',
'청산액',
'손실을 입으면서',
'시장 손실',
'long traders',
'더 많은 손실',

'cloud mining',
'클라우드 마이닝',
'passive income',
'수동 소득',
'quantitative trading',
'트레이딩 플랫폼 비교',
'ultimate passive income showdown',

'whales woke up',
'whale activity',
'whales are selling',
'고래들이 활동을 재개',
'고래들 움직임',
'고래 매도',

'what to expect next week',
'what to expect',
'next week',
'예상되는 사항',
'예상 기사',

'high yield',
'apr',
'30 apr',
'leading high-yield opportunities',
'예치 시',
'예치하면',
'이자 제공',
'고수익 기회',

'investment guide',
'top 7 ways to earn eth',
'earn eth',
'build passive income',
'staking',
'lending',
'스테이킹',
'대출 등으로',
'수익 받는 방법',
'lost',
'loss',
'losses',
'sell at a loss',
'underwater',
'worst quarter',
'worst first quarter',
'first quarter since',
'glassnode report',
'glassnode',
'traders lost',
'손실',
'손실을 확정',
'최악의 분기',
'최악의 분기 이후',
'분석 보고서',
'canton',
'캔톤',
'canton token',
'canton network',
	
	
    'long', 'short', '롱', '숏', '롱 포지션', '숏 포지션', 'liquidation', 'liquidations',
    '시장 심리', 'market sentiment',
    'moew', 'realgo', 'fast or go home', 'challenge', 'cfd',
    'allunity', 'kalqix', 'kalaix', 'mainnet launch', 'clob dex',

]






BAD_SIGNAL_PATTERNS = [
    r'\bno bullish reversal\b',
    r'\bno bullish reversal signs\b',
    r'\bweak price action\b',
    r'\bbearish\b',
    r'\bprice react\b',
    r'\bbullish crossover\b',
    r'\bcrossover completes\b',
    r'\bprice analysis\b',
    r'\bdowntrend\b',
    r'강세 전환 신호 없음',
    r'반등 신호 없음',
    r'하락세',
    r'약세',
    r'가격 상승으로 이어지지 못',
    r'상승으로 이어지지 못',
    r'반등 실패',
    r'크로스오버',
]
BAD_TOPIC_PATTERNS = [
    # 가격/차트/기술적 분석
    r'\bprice analysis\b',
    r'\bprice prediction\b',
    r'\bforecast\b',
    r'\bchart\b',
    r'\btechnical analysis\b',
    r'\btrading setup\b',
    r'\bsupport\b',
    r'\bresistance\b',
    r'\bbreakout\b',
    r'\btrend line\b',
    r'\bentry zone\b',
    r'\btarget price\b',
    r'\bbullish\b',
    r'\bbearish\b',
    r'\bcrossover\b',
    r'\bdeath cross\b',
    r'\bgolden cross\b',

    # 기술/개발/업그레이드/인프라
    r'\bdeveloper\b',
    r'\bdevelopers\b',
    r'\bdevnet\b',
    r'\btestnet\b',
    r'\bmainnet\b',
    r'\bupgrade\b',
    r'\bprotocol\b',
    r'\binfrastructure\b',
    r'\bsmart contract\b',
    r'\bsmart contracts\b',
    r'\bwallet security\b',
    r'\bquantum resilience\b',
    r'\bquantum resistance\b',
    r'\bpost-quantum\b',
    r'\blayer 2\b',
    r'\blayer2\b',

    # 입출금/전송/지갑
    r'입금',
    r'출금',
    r'입출금',
    r'전송',
    r'송금',
    r'deposit',
    r'withdraw',
    r'withdrawal',

    # 한국어 가격/분석 표현
    r'가격 분석',
    r'기술적 분석',
    r'차트 분석',
    r'지지선',
    r'저항선',
    r'목표가',
    r'돌파',
    r'반등',
    r'추세',
    r'매수 구간',
    r'매도 구간',

    # 한국어 기술/개발 표현
	

	r'\blisting\b',
    r'\blistings\b',
    r'\bdelisting\b',
    r'\bdelist\b',
    r'상장',
    r'상장 폐지',
    r'폐지 결정',
    r'거래지원 종료',
	# 시장 해설 / 분석 기사 제외
    r'\bcorrelation\b',
    r'\bsp correlation\b',
    r'\bs&p correlation\b',
    r'\bbull sign\b',
    r'\bnot the bull sign\b',
    r'강세 신호',
    r'분석이 나옴',
    r'상관관계',
    r'역상관',

    # 해킹 / 범죄 / 사기 기사 제외
    r'\bhack\b',
    r'\bhacker\b',
    r'\bhacked\b',
    r'\bscam\b',
    r'\bfraud\b',
    r'\bsocial engineering\b',
    r'\bcharged\b',
    r'\bprison sentence\b',
    r'\bstolen funds\b',
    r'해킹',
    r'사기',
    r'기소',
    r'검찰',
    r'징역',
    r'탈취',

    # 일반 금융 인프라 / 토큰화 일반 기사 제외
    r'\btokenized\b',
    r'\bdata infrastructure\b',
    r'\bcanton network\b',
    r'\bus treasuries\b',
    r'\biBoxx\b',
    r'\bs&p dow jones\b',
    r'미국채',
    r'데이터 인프라',
    r'칸톤네트워크',
    r'금융 데이터',
	r'\bactive users?\b',
    r'\bmarket recovery\b',
    r'\btrading assistant\b',
    r'\bretail users?\b',
    r'\bmonthly close\b',
    r'\bapril fools\b',
    r'\bipo controversy\b',
	r'\btransaction fee\b',
    r'\bfees\b',
    r'\binscription\b',
    r'\binscriptions\b',
    r'\bsoft fork\b',
    r'\bsoftfork\b',
    r'\bblock space\b',
    r'\bblocksize\b',
    r'\bblock size\b',
    r'\bthroughput\b',
    r'트랜잭션 수수료',
    r'인스크립션',
    r'소프트포크',
    r'블록당 트랜잭션',
    r'블록 용량',
	r'\bbollinger\b',
r'\bbollinger bands\b',
r'\bmajor move\b',
r'\btightening\b',
r'\bgolden cross\b',
r'\bburn rate\b',
r'\bnetwork activity\b',

	r'\bliquidation imbalance\b',
r'\bliquidations\b',
r'\bwhales woke up\b',
r'\bwhale activity\b',
r'\bwhat to expect\b',
r'\bnext week\b',
r'\bhigh yield\b',
r'\bpassive income\b',
r'\binvestment guide\b',
r'\bearn eth\b',
r'\bstaking\b',
r'\blending\b',
r'청산 불균형',
r'청산액',
r'고래들 움직임',
r'예상되는 사항',
r'고수익 기회',
r'수익 받는 방법',
r'스테이킹',
r'대출 등으로',

r'\blost\b',
r'\bloss(es)?\b',
r'\bworst quarter\b',
r'\bunderwater\b',
r'\bsell at a loss\b',
r'손실',
r'최악의 분기',
r'\bcanton\b',
r'캔톤',
	
	
]


NON_PORTFOLIO_ASSET_PATTERNS = [
    r'\bsol\b', r'\bsolana\b', r'\bdoge\b', r'\bdogecoin\b', r'\bavax\b',
    r'\bdot\b', r'\blink\b', r'\bltc\b', r'\bnear\b', r'\buni\b', r'\baave\b',
    r'\bpepe\b', r'\bwif\b', r'\bbonk\b', r'\bsui\b', r'\bapt\b', r'\batom\b',
    r'\bfil\b', r'\bhbar\b', r'\bkas\b', r'\btao\b', r'\bicp\b',
    r'솔라나', r'도지', r'아발란체', r'폴카닷', r'체인링크', r'라이트코인',
    r'니어', r'유니스왑', r'에이브', r'수이', r'앱토스', r'파일코인',
]


STOCK_PATTERNS = [
    r'\bstock\b',
    r'\bstocks\b',
    r'\bshare\b',
    r'\bshares\b',
    r'\bequity\b',
    r'\bdividend\b',
    r'\bearnings\b',
    r'\bshareholder\b',
    r'\bnasdaq\b',
    r'\bnyse\b',
    r'\bipo\b',
    r'주식',
    r'주가',
    r'배당',
    r'실적',
    r'주주',
    r'상장사',
]

def contains_non_portfolio_asset(text: str) -> bool:
    low = (text or "").lower()
    return any(re.search(p, low, re.I) for p in NON_PORTFOLIO_ASSET_PATTERNS)

def contains_stock_context(text: str) -> bool:
    low = (text or "").lower()
    return any(re.search(p, low, re.I) for p in STOCK_PATTERNS)

def contains_bad_signal(text: str) -> bool:
    low = (text or "").lower()
    return any(re.search(p, low, re.I) for p in BAD_SIGNAL_PATTERNS)

def contains_bad_topic(text: str) -> bool:
    low = (text or "").lower()
    return any(re.search(p, low, re.I) for p in BAD_TOPIC_PATTERNS)

def is_chart_or_price_article(text: str) -> bool:
    low = (text or "").lower()

    chart_patterns = [
        r'\bprice\b',
        r'가격',
        r'월봉',
        r'monthly candle',
        r'monthly chart',
        r'\bchart\b',
        r'\bcandlestick\b',
        r'\bsupport\b',
        r'\bresistance\b',
        r'\bbreakout\b',
        r'\btarget price\b',
        r'\bforecast\b',
        r'\bprice prediction\b',
        r'\btechnical analysis\b',
        r'기술적 분석',
        r'차트 분석',
        r'지지선',
        r'저항선',
        r'목표가',
        r'반등',
        r'선을\s*유지',
        r'선\s*유지',
        r'깨짐',
        r'뚫음',
        r'뚫림',
        r'유지함',
        r'유지 중',
        r'돌파',
        r'추세',
        r'공포탐욕',
        r'extreme fear',
        r'fear and greed',
        r'bottom signal',
        r'fails to break higher',
        r'price fails to break higher',
        r'green monthly candle',
        r'red monthly streak',
		r'lower highs',
r'price correction',
r'resistance range',
r'resistance level',
r'what s next',
r'what’s next',
r'tumbling',
r'continue to dip',
r'oscillate between',
		
    ]

    return any(re.search(p, low, re.I) for p in chart_patterns)


def is_refusal_or_skip_text(text: str) -> bool:
    low = (text or "").strip().lower()
    if not low:
        return True

    bad_phrases = [
        '죄송하지만',
        '요약문을 제공할 수 없음',
        '제공할 수 없음',
        '가격 차트',
        '기술적 분석 성격 기사',
        '차트·기술적 분석',
        '차트/기술적 분석',
        'cannot provide',
        'unable to provide',
        'technical analysis',
        'price chart',
    ]
    return any(p in low for p in bad_phrases)


def is_xrp_narrative_article(text: str) -> bool:
    low = (text or "").lower()

    xrp_terms = [
        'xrp', 'ripple', 'xrpl', 'xrp ledger', 'xrpledger',
        '리플', '엑스알피'
    ]

    narrative_terms = [
        'bank charter', 'occ', 'approval', 'custody', 'payment',
        'institutional', 'adoption', 'integration', 'volume',
        'liquidity', 'settlement', 'infrastructure',
        '은행 인가', '승인', '수탁', '결제', '기관', '도입', '통합', '인프라'
    ]

    has_xrp = any(contains_exact_term(low, t) for t in xrp_terms)
    has_narrative = any(contains_exact_term(low, t) for t in narrative_terms)

    return has_xrp and has_narrative


def is_pure_macro_article(text: str) -> bool:
    low = (text or "").lower()

    macro_terms = [
        'stablecoin', 'regulation', 'bill', 'law', 'policy', 'senate', 'house',
        'fed', 'treasury', 'bank', 'custody', 'occ', 'cftc', 'sec',
        '감시', '감독', '규제', '법안', '정책', '상원', '하원',
        '연준', '재무부', '은행', '수탁', '스테이블코인', 'OCC', 'SEC', 'CFTC'
    ]

    return any(contains_exact_term(low, t) for t in macro_terms)


FINAL_HASHTAGS = ['BTC','비트코인','dooridoori','도리도리','doorinati','도리나티']

INLINE_TAG_WHITELIST = {
    '미국', 'CFTC', 'Polymarket', '폴리마켓', 'Elizabeth Warren', '엘리자베스워런',
    '정부', '비트코인', 'BTC', 'ETH', 'XRP',
    '연준', 'SEC', 'ETF', '재무부', '상원', '하원',
    '아이언라이트', '보어히스', '에릭보어히스',
    '마이클세일러', '세일러', '로버트기요사키', '폴앳킨스',
    '데이비드슈워츠', '마이크노보그라츠', '샘알트만', '일론머스크',
    '셰이프시프트', '갈링하우스', '모니카롱', '비탈릭부텔린',
    '사토시나카모토', '저스틴썬', '제드맥케일럽', '찰스호스킨슨',
    '골드만삭스', '스트래티지', '도널드트럼프', '트럼프',
    '로빈후드', '테더', '리플', '플레어', '아테나', '에테나',
    '메타플래닛', '도리뉴스', '시바이누', '시바리움',
    '연준', '재무부', '백악관',
    '브라질', '중국', '일본', '한국', '미국', '이란', '이스라엘', '카타르',
    '마스터카드',
    'SEC', 'CFTC', 'OCC', 'ETF', 'IPO', 'CTO',
    'XRP', 'XLM', 'BTC', 'ETH', 'SHIB', 'USDC', 'USDT', 'XAUT', 'SOL', 'DOGE',
    'RLUSD', 'FOMC', '헤스터피어스', '시카고상품거래소', '키발리스', '라울팔', '누바', '템포', '머니그램', '미카', '도호쿠은행', 'SBIRemit', '소프트뱅크', '트웬티원캐피털', '화이트비트', '티머시매사드', '무로', '산탄데르',
    '비트코인', '이더리움', '스테이블코인', '토큰화', '수탁', '시드문구', '소송', '규제', '해석',
    'DeFi', 'NFT', 'Web3', '디파이', '엑스알피',
    'BitMine', '비트마인',
    '톰리', '제롬파월', '파월',
    '네비다주', 'JPMorgan', '라이드', '바이비트', 'Ledger',
    '서클', '머니그램', '업비트', '빗썸', '바이낸스',
    '애플', '페이팔', '스트라이프', '제미니', '칼시', '제드시온',
    '에버노스', 'XRPLedger', '세계금협회',
     '디지털금', '비트코인퀀텀', 'BIP360',
    'OpenAI', 'Anthropic', '슈퍼마이크로', 'AI', 'LNG',
    '바잔', '캘리포니아', '모건스탠리', '크라켄',
    '지니어스법안', '지니어스', '법안', 'ICE', '클래리티',
    '블랙록', '문페이', '코인베이스', '히든로드', '게임스탑',
    '구글', '인도', '웰스파고', '피터쉬프', '패니매',
    'EEZ', '버핏',
    '스트라이브', '터틀', '스트라이브자산운용', 'STRC', 'SATA', '니움', '비자',
    '오픈크레딧', '스마트계약', '프라이빗크레딧', '기관자금',
	'Bitcoin', 'Ethereum', 'Ripple','United States', 'US', 'Government',
'Federal Reserve', 'Fed', 'Treasury', 'Senate', 'House', 'White House',

'Ironlight', 'Vorhees', 'Erik Vorhees',
'Michael Saylor', 'Saylor', 'Robert Kiyosaki', 'Paul Atkins',
'David Schwartz', 'Mike Novogratz', 'Sam Altman', 'Elon Musk',
'ShapeShift', 'Brad Garlinghouse', 'Garlinghouse', 'Monica Long', 'Vitalik Buterin',
'Satoshi Nakamoto', 'Justin Sun', 'Jed McCaleb', 'Charles Hoskinson',
'Goldman Sachs', 'Strategy', 'Donald Trump', 'Trump',
'Robinhood', 'Tether', 'Ripple', 'Flare', 'ATHENA', 'Ethena',
'Metaplanet', 'DooriNews', 'Shiba Inu', 'Shibarium',

'Brazil', 'China', 'Japan', 'Korea', 'South Korea', 'Iran', 'Israel', 'Qatar',
'Mastercard', 'Visa',

'SEC', 'CFTC', 'OCC', 'ETF', 'IPO', 'CTO',
'XRP', 'XLM', 'BTC', 'ETH', 'SHIB', 'USDC', 'USDT', 'XAUT', 'SOL', 'DOGE',
    'RLUSD', 'FOMC', '헤스터피어스', '시카고상품거래소', '키발리스', '라울팔', '누바', '템포', '머니그램', '미카', '도호쿠은행', 'SBIRemit', '소프트뱅크', '트웬티원캐피털', '화이트비트', '티머시매사드', '무로', '산탄데르',

'Bitcoin', 'Ethereum', 'Stablecoin', 'Tokenization', 'Custody', 'Seed Phrase',
'Lawsuit', 'Regulation', 'Interpretation',

'DeFi', 'NFT', 'Web3',
'BitMine',
'Tom Lee', 'Jerome Powell', 'Powell',
'Nevada', 'JPMorgan', 'Ryde', 'Bybit', 'Ledger',
'Circle', 'MoneyGram', 'Upbit', 'Bithumb', 'Binance',
'Apple', 'PayPal', 'Stripe', 'Gemini', 'Kalshi', 'Zedxion',
'Evernorth', 'XRPLedger', 'World Gold Council',
'Gold', 'Digital Gold', 'Silver', 'Bitcoin Quantum', 'BIP360',
'OpenAI', 'Anthropic', 'Super Micro', 'AI', 'LNG',
'BAZAN', 'California', 'Morgan Stanley', 'Kraken',
'Genius Act', 'Genius', 'Act', 'ICE', 'CLARITY',
'BlackRock', 'MoonPay', 'Coinbase', 'Hidden Road', 'GameStop',
'Google', 'India', 'Wells Fargo', 'Peter Schiff', 'Fannie Mae',
'EEZ', 'Buffett',
'Strive', 'Tuttle', 'Strive Asset Management', 'STRC', 'SATA', 'Nium',
'Open Credit', 'Smart Contract', 'Smart Contracts', 'Private Credit', 'Private Credits', 'Institutional Capital',
'BCH', 'Bitcoin Cash', '비트코인캐시',
'노동부', 'U.S. Department of Labor', 'US Department of Labor', 'Department of Labor', 'Labor Department',
	'밈코인','Mimcoin','금융', '암호화폐', '트론', 'TRX', 'TRON', '호주', '미국',
'BitGo', 'TRON', 'TRX', 'Australia', 'Franklin Templeton', 'Tony Pecore',
'프랭클린템플턴', '토니피코어','WisdomTree', '위즈덤트리', 'CLARITY Act', '클래리티법','Jack Dorsey', '잭도시', 'Block',
'Michael Selig', '마이클셀릭', '마이클 셀릭','마이크로소프트', 'Microsoft','XRPL', 'DEX', '탈중앙거래소', 'DeFi', 'Vet', '사토시쿠사마',
'XRPL', 'DEX', 'Decentralized Exchange', 'Satoshi Kusama',

	'Bitdeer', '비트디어','Blockstream', '블록스트림','IMF', '토비아스아드리안', 'Tobias Adrian', 'RWA', '지니어스법안','Charles Schwab', '찰스슈왑',
'Oracle', '오라클','피터쉬프', 'Peter Schiff','금융당국', '사모대출', '잉글랜드은행', '앤드루베일리',
'한국은행', '보험연수원', '디지털화폐', '디지털통화', '지수보험',
'일본은행', '유가', '국채', '신현송', 'CBDC',
'메타플래닛', '일본 정부', '코인원', '코인원 AML',
'ABA', '예금', '은행예금', '금융위원회',
'모니카롱', 'ODL', 'FedNow', 'Fedwire',
'금융상품거래법', '금융상품', '스테이블코인', '클래리티법안',
'브래드갈링하우스', '리플 CEO', '블랙록 CEO',
'SMQKE', '신탁은행', '마스터계정', '금융감독청',
'주택시장', '제프박', '프로캡',
'업비트', 'USDT', '원화마켓', 'KRW',

	
	
}



MANUAL_TRANSLATIONS = {
    'Polymarket': '폴리마켓',
    '폴리마켓': '폴리마켓',

    'Ironlight': '아이언라이트',
    '아이언라이트': '아이언라이트',

    'Vorhees': '보어히스',
    '보어히스': '보어히스',

    'Erik Vorhees': '에릭보어히스',
    '에릭보어히스': '에릭보어히스',

    'Michael Saylor': '마이클세일러',
    '마이클세일러': '마이클세일러',

    'Saylor': '세일러',
    '세일러': '세일러',

    'Robert Kiyosaki': '로버트기요사키',
    '로버트기요사키': '로버트기요사키',

    'Paul Atkins': '폴앳킨스',
    '폴앳킨스': '폴앳킨스',

    'David Schwartz': '데이비드슈워츠',
    '데이비드슈워츠': '데이비드슈워츠',

    'Mike Novogratz': '마이크노보그라츠',
    '마이크노보그라츠': '마이크노보그라츠',

    'Sam Altman': '샘알트만',
    '샘알트만': '샘알트만',

    'Elon Musk': '일론머스크',
    '일론머스크': '일론머스크',

    'ShapeShift': '셰이프시프트',
    '셰이프시프트': '셰이프시프트',

    'Brad Garlinghouse': '갈링하우스',
	'Grlinghouse':'갈링하우스',
    '갈링하우스': '갈링하우스',

    'Monica Long': '모니카롱',
    '모니카롱': '모니카롱',

    'Vitalik Buterin': '비탈릭부텔린',
    '비탈릭부텔린': '비탈릭부텔린',
    'FOMC': 'FOMC',
    '헤스터 피어스': '헤스터피어스',
    'Hester Peirce': '헤스터피어스',
    'CME': '시카고상품거래소',
    'CME Group': '시카고상품거래소',
    'Chicago Mercantile Exchange': '시카고상품거래소',
    'Qivalis': '키발리스',
    '키발리스': '키발리스',
    'Raoul Pal': '라울팔',
    '라울 팔': '라울팔',
    '라울팔': '라울팔',
    'NUVA': '누바',
    'Tempo': '템포',
    'MoneyGram': '머니그램',
    'RLUSD': 'RLUSD',
    'MiCA': '미카',
    'MICA': '미카',
    'AllUnity': '올유니티',
    'Kalqix': '칼릭스',
    'KalaiX': '칼릭스',
    'Tohoku Bank': '도호쿠은행',
    'SBI Remit': 'SBIRemit',
    'SoftBank': '소프트뱅크',
    'Twenty One Capital': '트웬티원캐피털',
    'XXI': 'XXI',
    'WhiteBIT': '화이트비트',
    'Timothy Massad': '티머시매사드',
    'Morgan Stanley': '모건스탠리',
    'Truth Social': '트루스소셜',
    'Santiment': '샌티먼트',
    'Muro': '무로',
    'Santander': '산탄데르',


    'Satoshi Nakamoto': '사토시나카모토',
    '사토시나카모토': '사토시나카모토',
	'Nakamoto': '나카모토',
    '나카모토': '나카모토',

    'Justin Sun': '저스틴썬',
    '저스틴썬': '저스틴썬',

    'Jed McCaleb': '제드맥케일럽',
    '제드맥케일럽': '제드맥케일럽',

    'Charles Hoskinson': '찰스호스킨슨',
    '찰스호스킨슨': '찰스호스킨슨',

    'Goldman Sachs': '골드만삭스',
    '골드만삭스': '골드만삭스',

    'Strategy': '스트래티지',
    '스트래티지': '스트래티지',

    'Donald Trump': '도널드트럼프',
    '도널드트럼프': '도널드트럼프',

    'Trump': '트럼프',
    '트럼프': '트럼프',

	'Jack Dorsey': '잭도시',
    '잭 도시': '잭도시',
    '잭도시': '잭도시',
    'Block': 'Block',

    'Robinhood': '로빈후드',
    '로빈후드': '로빈후드',

    'Tether': '테더',
    '테더': '테더',

    'Ripple': 'XRP',
    '리플': 'XRP',

	'TRX': '트론',
    'TRON': '트론',

    'Flare': '플레어',
    '플레어': '플레어',

    'FLR': 'FLR',
    'ATHENA': '아테나',
    '아테나': '아테나',

    'ENA': '에테나',
    'Ethena': '에테나',
    '에테나': '에테나',

    'Metaplanet': '메타플래닛',
    '메타플래닛': '메타플래닛',

    'DooriNews': '도리뉴스',
    '도리뉴스': '도리뉴스',

    'Shiba Inu': '시바이누',
    '시바이누': '시바이누',
    '시바견': '시바이누',

    'Shibarium': '시바리움',
    '시바리움': '시바리움',

    'Swift': 'SWIFT',

    'Fed': '연준',
    'Federal Reserve': '연준',
    '연준': '연준',

    'Treasury': '재무부',
    '재무부': '재무부',

    'White House': '백악관',
    '백악관': '백악관',

    'Brazil': '브라질',
    '브라질': '브라질',

    'China': '중국',
    '중국': '중국',

    'Japan': '일본',
    '일본': '일본',

    'Korea': '한국',
    'South Korea': '한국',
    '한국': '한국',

    'United States': '미국',
    'US': '미국',
    '미국': '미국',

    'Iran': '이란',
    '이란': '이란',

    'Israel': '이스라엘',
    '이스라엘': '이스라엘',

    'Qatar': '카타르',
    '카타르': '카타르',

    'mastercard': '마스터카드',
    'Mastercard': '마스터카드',
    '마스터카드': '마스터카드',

    'SEC': 'SEC',
    'CFTC': 'CFTC',
    'OCC': 'OCC',
    'ETF': 'ETF',
    'IPO': 'IPO',
    'CTO': 'CTO',
    'XRP': 'XRP',
    'XLM': 'XLM',
    'BTC': 'BTC',
    'ETH': 'ETH',
    'SHIB': 'SHIB',
    'USDC': 'USDC',
    'USDT': 'USDT',
    'XAUT': 'XAUT',
    'SOL': 'SOL',
    'DOGE': 'DOGE',

    'Bitcoin': '비트코인',
    '비트코인': '비트코인',

    'Ethereum': '이더리움',
    '이더리움': '이더리움',

    'Stablecoin': '스테이블코인',
    'stablecoin': '스테이블코인',
    '스테이블코인': '스테이블코인',

    'Tokenization': '토큰화',
    '토큰화': '토큰화',

    'Custody': '수탁',
    '수탁': '수탁',

    'Seed Phrase': '시드문구',
    '시드문구': '시드문구',

    'Lawsuit': '소송',
    '소송': '소송',

    'Regulation': '규제',
    '규제': '규제',

    'Interpretation': '해석',
    '해석': '해석',

    'DeFi': 'DeFi',
    '디파이': 'DeFi',

    'NFT': 'NFT',
    'Web3': 'Web3',

    'BitMine': '비트마인',
    '비트마인': '비트마인',

    'Tom Lee': '톰리',
    '톰리': '톰리',

    'Thomasg.eth': 'Thomasgeth',
    'Time Traveler': 'TimeTraveler',
    'John Squire': 'JohnSquire',

    'Uniswap': '유니스왑',
    '유니스왑': '유니스왑',

    'Hayden Adams': 'HaydenAdams',

    'Jerome Powell': '제롬파월',
    'Powell': '파월',
    '제롬파월': '제롬파월',
    '파월': '파월',

    'America': '미국',

    'Nevada': '네비다주',
    '네비다주': '네비다주',

    'J.P. Morgan': 'JPMorgan',
    'JP Morgan': 'JPMorgan',
    'JPMorgan': 'JPMorgan',
    '제이피모건': 'JPMorgan',

    'Ryde': '라이드',
    '라이드': '라이드',

    'Bybit': '바이비트',
    '바이비트': '바이비트',

    'Ledger': 'Ledger',
    '서클': '서클',
    'Circle': '서클',

    'MoneyGram': '머니그램',
    '머니그램': '머니그램',

    'Upbit': '업비트',
    '업비트': '업비트',

    'Bithumb': '빗썸',
    '빗썸': '빗썸',

    'Binance': '바이낸스',
    '바이낸스': '바이낸스',

    'Apple': '애플',
    '애플': '애플',

    'PayPal': '페이팔',
    '페이팔': '페이팔',

    'Stripe': '스트라이프',
    '스트라이프': '스트라이프',

    'Gemini': '제미니',
    '제미니': '제미니',

    'Kalshi': '칼시',
    '칼시': '칼시',

    'Zedxion': '제드시온',
    '제드시온': '제드시온',

    'Evernorth Holdings': '에버노스',
    'Evernorth': '에버노스',
    '에버노스': '에버노스',

    'XRPLedger': 'XRPLedger',
    'XRP Ledger': 'XRPLedger',

    'World Gold Council': '세계금협회',
    '세계금협회': '세계금협회',

    'Gold': '금',
    '금': '금',

    'Digital Gold': '디지털금',
    '디지털금': '디지털금',

    'Silver': '은',
    '은': '은',

    'Bitcoin Quantum': '비트코인퀀텀',
    '비트코인퀀텀': '비트코인퀀텀',

    'BIP360': 'BIP360',

    'OpenAI': 'OpenAI',
    '오픈에이아이': 'OpenAI',

    'Anthropic': 'Anthropic',
    '앤트로픽': 'Anthropic',

    'Super Micro': '슈퍼마이크로',
    '슈퍼마이크로': '슈퍼마이크로',

    'AI': 'AI',
    'LNG': 'LNG',

    'BAZAN': '바잔',
    '바잔': '바잔',

    'California': '캘리포니아',
    '캘리포니아': '캘리포니아',

    'Morgan Stanley': '모건스탠리',
    'MorganStanley': '모건스탠리',
    '모건스탠리': '모건스탠리',

    'Kraken': '크라켄',
    '크라켄': '크라켄',

    'Genius Act': '지니어스법안',
    '지니어스법안': '지니어스법안',
    'Genius': '지니어스',
    '지니어스': '지니어스',
    'Act': '법안',
    '법안': '법안',

    'ICE': 'ICE',

    'CLARITY': '클래리티',
    '클래리티': '클래리티',

    'Blackrock': '블랙록',
    'BlackRock': '블랙록',
    '블랙록': '블랙록',

    'MoonPay': '문페이',
    '문페이': '문페이',

    'coinbase': '코인베이스',
    'Coinbase': '코인베이스',
    '코인베이스': '코인베이스',

    'Hidden Road': '히든로드',
    '히든로드': '히든로드',

    'GameStop': '게임스탑',
    '게임스탑': '게임스탑',

    'Google': '구글',
    '구글': '구글',

    'India': '인도',
    '인도': '인도',

    'Wells Fargo': '웰스파고',
    '웰스파고': '웰스파고',

    'Peter Schiff':'Peter Schiff', 
    '피터 쉬프':'피터쉬프',

    'Fannie Mae':'FannieMae', 
    '패니 매':'패니매',

	'EEZ':'EEZ',

	'Buffett':'버핏',

	'Strive': '스트라이브',
    'Tuttle': '터틀',
    'Strive Asset Management': '스트라이브자산운용',
    'STRC': 'STRC',
    'SATA': 'SATA',
    'Nium': '니움',
    'NIUM': '니움',
	'Visa': '비자',
    'Mastercard': '마스터카드',
	'DeFi': '디파이',
    '디파이': '디파이',
    'Open Credit': '오픈크레딧',
    'OpenCredit': '오픈크레딧',
    '오픈크레딧': '오픈크레딧',
    'Smart Contract': '스마트계약',
    'Smart Contracts': '스마트계약',
    'Private Credit': '프라이빗크레딧',
    'Private Credits': '프라이빗크레딧',
    '프라이빗크레딧': '프라이빗크레딧',
    'Institutional Capital': '기관자금',
    '기관자금': '기관자금',
	'Elizabeth Warren': '엘리자베스워런',
    '엘리자베스 워런': '엘리자베스워런',
    '엘리자베스워런': '엘리자베스워런',
    'Government': '정부',
    '정부': '정부',
	'Bitcoin Cash': '비트코인캐시',
    '비트코인캐시': '비트코인캐시',
    'BCH': 'BCH',

    'U.S. Department of Labor': '노동부',
    'US Department of Labor': '노동부',
    'Department of Labor': '노동부',
    'Labor Department': '노동부',
    '노동부': '노동부',

    '401(k)': '401k',
	'401 k': '401k',
    '401K': '401k',
    '401k': '401k',
	'mim coin':'밈코인',
	'밈코인':'밈코',

	'TRON': '트론',
    'TRX': '트론',
    '트론': '트론',
    'Australia': '호주',
    'Australian': '호주',
    '호주': '호주',
    'Franklin Templeton': '프랭클린템플턴',
    '프랭클린템플턴': '프랭클린템플턴',
    'Tony Pecore': '토니피코어',
    '토니피코어': '토니피코어',
    'Crypto': '암호화폐',
    'crypto': '암호화폐',
    '암호화폐': '암호화폐',
    'Finance': '금융',
    'financial': '금융',
    '금융': '금융',
	'WisdomTree': '위즈덤트리',
    '위즈덤트리': '위즈덤트리',
    'CLARITY Act': '클래리티법',
    '클래리티법': '클래리티법',
	    'Michael Barr': '마이클바',
    '마이클 바': '마이클바',
    '마이클바': '마이클바',

    'GENIUS': 'GENIUS',
    'Genius Act': '지니어스법',
    '지니어스법': '지니어스법',

    'Australia': '호주',
    'Australian': '호주',
    '호주': '호주',

    'Custodian': '수탁업체',
    'Custodians': '수탁업체',
    '수탁업체': '수탁업체',

    'Hong Kong': '홍콩',
    '홍콩': '홍콩',

    'HKMA': '홍콩금융관리국',
    'Hong Kong Monetary Authority': '홍콩금융관리국',
    '홍콩금융관리국': '홍콩금융관리국',

    'HSBC': 'HSBC',
    'Standard Chartered': '스탠다드차타드',
    '스탠다드차타드': '스탠다드차타드',

	'Michael Selig': '마이클셀릭',
    '마이클 셀릭': '마이클셀릭',
    '마이클셀릭': '마이클셀릭',
	'Paul Grewal': '폴그루월',
'폴 그루월': '폴그루월',
'폴그루월': '폴그루월',
'Grewal': '그루월',
'그루월': '그루월',

'Brad Garlinghouse': '브래드갈링하우스',
'브래드 갈링하우스': '브래드갈링하우스',
'브래드갈링하우스': '브래드갈링하우스',
'CEO': 'CEO',

'Genius Group': '지니어스그룹',
'지니어스그룹': '지니어스그룹',

'Government': '정부',
'정부': '정부',
'KYC': 'KYC',

'FTX': 'FTX',
'Nishad Singh': '니샤드싱',
'니샤드 싱': '니샤드싱',
'니샤드싱': '니샤드싱',

'KBank': '케이뱅크',
'케이뱅크': '케이뱅크',

'eToro': 'eToro',
'Taiwan': '대만',
'대만': '대만',

'Coinone': '코인원',
'코인원': '코인원',

'Bitget': '비트겟',
'비트겟': '비트겟',
'SafePal': '세이프팔',
'세이프팔': '세이프',

'Microsoft': '마이크로소프트',
'마이크로소프트': '마이크로소프트',
	
'David Schwartz': '데이비드슈워츠',
'데이비드슈워츠': '데이비드슈워츠',
	
'Ripple': 'XRP',
'리플': 'XRP',
	'XRPL': 'XRPL',
'DEX': 'DEX',
'Decentralized Exchange': '탈중앙거래소',
'탈중앙거래소': '탈중앙거래소',
'Satoshi Kusama': '사토시쿠사마',
    'XRP Ledger': 'XRPLedger',
    'xrp ledger': 'XRPLedger',
    'RLUSD': 'RLUSD',
    'FOMC': 'FOMC',
    'Hester Peirce': '헤스터피어스',
    'CME Group': '시카고상품거래소(CME)',
    'Chicago Mercantile Exchange': '시카고상품거래소(CME)',
    'Qivalis': '키발리스',
    'Raoul Pal': '라울팔',
    'NUVA': '누바',
    'Tempo': '템포',
    'MoneyGram': '머니그램',
    'MiCA': '미카',
    'MICA': '미카',
    'AllUnity': '올유니티',
    'Kalqix': '칼릭스',
    'KalaiX': '칼릭스',
    'Truth Social': '트루스소셜',
    'Tohoku Bank': '도호쿠은행',
    'SBI Remit': 'SBIRemit',
    'SoftBank': '소프트뱅크',
    'Twenty One Capital': '트웬티원캐피털',
    'Timothy Massad': '티머시매사드',
    'Santiment': '샌티먼트',
    'Santander': '산탄데르',

'사토시 쿠사마': '사토시쿠사마',
'사토시쿠사마': '사토시쿠사마',
'Vet': 'Vet',
'VET': 'Vet',
	'Bitdeer': '비트디어',
'비트디어': '비트디어',

	'Blockstream': '블록스트림',
'블록스트림': '블록스트림',

	'IMF': 'IMF',
'Tobias Adrian': '토비아스아드리안',
'토비아스 아드리안': '토비아스아드리안',
'토비아스아드리안': '토비아스아드리안',
'RWA': 'RWA',
'지니어스법안': '지니어스법안',
	'Charles Schwab': '찰스슈왑',
'찰스 슈왑': '찰스슈왑',
'찰스슈왑': '찰스슈왑',
'Oracle': '오라클',
'오라클': '오라클',

	'Peter Schiff': '피터쉬프',
'피터 쉬프': '피터쉬프',
'피터쉬프': '피터쉬프',
	'Financial Supervisory Service': '금융당국',
'금융당국': '금융당국',

'Private Credit': '사모대출',
'private credit': '사모대출',
'사모대출': '사모대출',

'Bank of England': '잉글랜드은행',
'잉글랜드은행': '잉글랜드은행',

'Andrew Bailey': '앤드루베일리',
'앤드루 베일리': '앤드루베일리',
'앤드루베일리': '앤드루베일리',

'Bank of Korea': '한국은행',
'한국은행': '한국은행',

'Korea Insurance Development Institute': '보험연수원',
'보험연수원': '보험연수원',

'Digital Currency': '디지털통화',
'디지털통화': '디지털통화',
'Digital Assets': '디지털자산',
'디지털자산': '디지털자산',
'Digital Finance': '디지털화폐',
'디지털화폐': '디지털화폐',

'Bank of Japan': '일본은행',
'일본은행': '일본은행',

'Hyun Song Shin': '신현송',
'신현송': '신현송',

'CBDC': 'CBDC',

'ABA': 'ABA',

'Monica Long': '모니카롱',
'모니카롱': '모니카롱',

'ODL': 'ODL',
'FedNow': 'FedNow',
'Fedwire': 'Fedwire',

'SMQKE': 'SMQKE',
'Master Account': '마스터계정',
'마스터계정': '마스터계정',
'Trust Bank': '신탁은행',
'신탁은행': '신탁은행',

'Jeff Park': '제프박',
'제프 박': '제프박',
'제프박': '제프박',

'ProCap': '프로캡',
'프로캡': '프로캡',

'Upbit': '업비트',
'업비트': '업비트',

'Coinone': '코인원',
'코인원': '코인원',
}


COUNTRY_TAG_MAP = {
    'US': ['미국', 'United States', 'US', 'U.S.', 'America'],
    'Korea': ['한국', '대한민국', 'South Korea', 'Korea'],
    'Japan': ['일본', 'Japan'],
    'China': ['중국', 'China'],
    'Taiwan': ['대만', 'Taiwan'],
    'HongKong': ['홍콩', 'Hong Kong'],
    'Australia': ['호주', 'Australia', 'Australian'],
    'Singapore': ['싱가포르', 'Singapore'],
    'Canada': ['캐나다', 'Canada'],
    'UK': ['영국', 'United Kingdom', 'UK', 'Britain'],
    'Germany': ['독일', 'Germany'],
    'France': ['프랑스', 'France'],
    'Brazil': ['브라질', 'Brazil'],
    'India': ['인도', 'India'],
    'UAE': ['아랍에미리트', 'UAE', 'United Arab Emirates'],
    'SaudiArabia': ['사우디아라비아', 'Saudi Arabia'],
    'Qatar': ['카타르', 'Qatar'],
    'Israel': ['이스라엘', 'Israel'],
    'Iran': ['이란', 'Iran'],
    'Turkey': ['튀르키예', '터키', 'Turkey', 'Türkiye'],
    'Russia': ['러시아', 'Russia'],
    'Ukraine': ['우크라이나', 'Ukraine'],
    'SouthAfrica': ['남아프리카공화국', '남아공', 'South Africa'],
    'Nigeria': ['나이지리아', 'Nigeria'],
    'Kazakhstan': ['카자흐스탄', 'Kazakhstan'],
	
}
COUNTRY_FINAL_TAGS = set()
COUNTRY_INLINE_ALIASES = set()
COUNTRY_TRANSLATIONS = {}

for final_tag, aliases in COUNTRY_TAG_MAP.items():
    ko = aliases[0]

    COUNTRY_FINAL_TAGS.add(f'#{final_tag}')
    COUNTRY_INLINE_ALIASES.update(aliases)

    for alias in aliases:
        COUNTRY_TRANSLATIONS[alias] = ko

for alias in COUNTRY_INLINE_ALIASES:
    if alias not in KOREAN_TAG_KEYWORDS:
        KOREAN_TAG_KEYWORDS.append(alias)

INLINE_TAG_WHITELIST.update(COUNTRY_INLINE_ALIASES)
MANUAL_TRANSLATIONS.update(COUNTRY_TRANSLATIONS)

IGNORED_WORDS = {
    'raises','posts','reports','appeared','appears','launches','launch','publishes','reveals',
    'acquires','funds','boosts','first','second','third','study','trial','trials','tests',
    'report','announces','announced','article','post','tokenized','markets','crypto','briefing',
    'listings','products','platform','analysis','market','digital','security','securities',
    'blockchain','regulated','marketplace','exchange','trading','website','visit',
    'records','record','says','said','say',
    'bridge','bridges','unlocks','unlock',
    'spikes','spike','activity','recent',
    'true','traditional','network',
    'here','what','about','if','daily','newsletter','excerpt','excerpts',
    'underpriced','asset','highlights','early','top','news',
    'regulation','EconomicGrowth', 'MarketsAreBetting', 'this','level','could','trigger','million','long','squeeze',
    'here','what','about','if','will','run','top','highlights','passes',
    'surprise','you','says','underpriced','asset','needs','hit',
    'does','this','mean','reserve','errors','year','peak','above',
    'insufficient','institutional','deals','long','game','hitting',
'metals','investments','hard','prices','fall','early','except','before','time','traveler','sell','one','time', 'hours', 'hour', 'market', 'markets', 'today', 'update',
    'daily', 'briefing', 'analysis', 'guest', 'post', 'article',
    'gas', 'prices', 'bond', 'panic', 'campaign', 'event', 'launch'
}
SITE_NAMES = {
    'CryptoBriefing','Cointelegraph','CryptoSlate','TheBlock','WatcherGuru','Cryptopolitan',
    'TheCryptoBasic','CoinGape','TimesTabloid','DailyHodl','BeInCrypto','BloomingBit','NewsBitcoin','CoinTurk'
}
CRYPTO_ACRONYMS = {'XRP','XLM','SEC','CFTC','OCC','BTC','ETH','USDC','USDT','XAUT',
    'DEFI','NFT','WEB3','ETP','ETF','DAO','IPO','CTO','LNG','AI',
}
STATE_FILE = 'news_state.json'
MAX_ITEMS_PER_FEED = 6
SUMMARY_SENTENCES = 3
OPENAI_INPUT_COST_PER_1M = 0.75
OPENAI_OUTPUT_COST_PER_1M = 4.50
AVG_CHARS_PER_TOKEN = 4
SHOW_COST_LOG = True

def normalize_url(url: str) -> str:
    url = (url or '').strip().lower()
    url = re.sub(r'^https?://', '', url)
    url = url.rstrip('/')
    return url

def log(msg: str) -> None:
    print(msg, flush=True)
	
def estimate_tokens_from_text(text: str) -> int:
    if not text:
        return 0
    return max(1, int(len(text) / AVG_CHARS_PER_TOKEN))


def log_openai_cost(title: str, prompt: str, output: str) -> None:
    if not SHOW_COST_LOG:
        return

    input_tokens = estimate_tokens_from_text(prompt)
    output_tokens = estimate_tokens_from_text(output)

    input_cost = (input_tokens / 1_000_000) * OPENAI_INPUT_COST_PER_1M
    output_cost = (output_tokens / 1_000_000) * OPENAI_OUTPUT_COST_PER_1M
    total_cost = input_cost + output_cost

    log(
        f"[OpenAI 비용] {title[:60]} | "
        f"입력토큰≈{input_tokens} | 출력토큰≈{output_tokens} | "
        f"예상비용≈${total_cost:.6f}"
    )

def has_precious_metal_context(text: str, metal: str) -> bool:
    raw = text or ""
    norm = normalize_text(raw)

    if metal == 'gold':
        patterns = [
            r'(^|\s)gold($|\s)',
            r'(^|\s)digital gold($|\s)',
            r'(^|\s)world gold council($|\s)',
            r'(^|\s)xaut($|\s)',
        ]
    elif metal == 'silver':
        patterns = [
            r'(^|\s)silver($|\s)',
        ]
    else:
        return False

    return any(re.search(p, norm, re.I) for p in patterns)

def http_get(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; DooriNewsBot/2.1)'})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode('utf-8', errors='ignore')

def story_hash(title: str) -> str:
    clean = re.sub(r'[^a-z0-9 ]', '', title.lower().strip())
    return hashlib.md5(clean.encode('utf-8')).hexdigest()[:12]

def load_state(path: str) -> dict:
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_state(path: str, state: dict):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def is_duplicate(title: str, posted: dict, url: str = "") -> bool:
    title_key = story_hash(title)
    if title_key in posted:
        return True

    norm_url = normalize_url(url)
    if norm_url:
        for item in posted.values():
            old_url = normalize_url(item.get('url', ''))
            if old_url and old_url == norm_url:
                return True

    return False

def update_posted(title: str, posted: dict, url: str = "", signature: str = "", canonical_key: str = ""):
    posted[story_hash(title)] = {
        'title': title,
        'url': normalize_url(url),
        'signature': signature,
        'canonical_key': canonical_key,
        'ts': datetime.now(timezone.utc).isoformat()
    }

def is_weak_text(text: str) -> bool:
    low = text.lower().strip()
    return (not low) or len(low) < 50 or 'visit website' in low or '웹사이트 방문' in low or bool(re.fullmatch(r'https?://\S+', low))

def extract_meta(html_text: str, names: list[str]) -> str:
    for name in names:
        pats = [
            rf'<meta[^>]+property=["\']{re.escape(name)}["\'][^>]+content=["\'](.*?)["\']',
            rf'<meta[^>]+name=["\']{re.escape(name)}["\'][^>]+content=["\'](.*?)["\']',
            rf'<meta[^>]+content=["\'](.*?)["\'][^>]+property=["\']{re.escape(name)}["\']',
            rf'<meta[^>]+content=["\'](.*?)["\'][^>]+name=["\']{re.escape(name)}["\']',
        ]
        for pat in pats:
            m = re.search(pat, html_text, re.I | re.S)
            if m:
                return html.unescape(m.group(1)).strip()
    return ""

def fetch_article_meta(url: str) -> tuple[str, str]:
    try:
        html_text = http_get(url, timeout=8)
    except Exception:
        return "", ""
    return (
        extract_meta(html_text, ['og:description','description','twitter:description']),
        extract_meta(html_text, ['og:image','twitter:image'])
    )

def fetch_rss(url: str, max_items: int = MAX_ITEMS_PER_FEED):
    stories = []
    try:
        data = http_get(url, timeout=12)
        root = ET.fromstring(data)
        for item in root.findall('.//item')[:max_items]:
            title = (item.findtext('title') or '').strip()
            link = (item.findtext('link') or '').strip()
            desc = (item.findtext('description') or '').strip()
            pub = (item.findtext('pubDate') or '').strip()

            desc_clean = re.sub(r'<[^>]+>', ' ', unescape(desc))
            desc_clean = re.sub(r'\s+', ' ', desc_clean).strip()

            image_url = ''
            try:
                media = item.find('{http://search.yahoo.com/mrss/}content') or item.find('{http://search.yahoo.com/mrss/}thumbnail')
                if media is not None and media.attrib.get('url'):
                    image_url = media.attrib['url']
                else:
                    enclosure = item.find('enclosure')
                    if enclosure is not None and enclosure.attrib.get('url'):
                        image_url = enclosure.attrib['url']

                if not image_url:
                    for child in item:
                        tag = str(child.tag).lower()
                        if 'thumbnail' in tag or 'content' in tag:
                            cand = child.attrib.get('url', '').strip()
                            if cand.startswith('http'):
                                image_url = cand
                                break
            except Exception:
                image_url = ''

            # 이미지 보강
            article_desc, article_img = ('', '')

            need_meta_fetch = (
                (not image_url)
                or (not str(image_url).startswith('http'))
                or ('coinedition.com' in link)
            )

            if need_meta_fetch:
                article_desc, article_img = fetch_article_meta(link)

            if article_img and str(article_img).startswith('http'):
                image_url = article_img

            if is_weak_text(desc_clean) and article_desc:
                desc_clean = article_desc

            if title and link:
                stories.append({
                    'title': unescape(title),
                    'url': link,
                    'desc': desc_clean,
                    'pub': pub,
                    'image_url': image_url
                })
    except Exception as e:
        log(f"Error fetching {url}: {e}")
    return stories

def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r'https?://\S+', ' ', text)
    text = re.sub(r'[^a-z0-9가-힣\s]', ' ', text)

    noise_words = [
        'says', 'said', 'claims', 'claim', 'predicts', 'predict', 'analyst', 'analysts',
        'expert', 'experts', 'report', 'reports', 'reported',
        'according to', 'could', 'may', 'might', 'will',
        'price prediction', 'forecast', 'outlook',
        'surges', 'jumps', 'rises', 'falls', 'drops',
        'here is', 'here’s', 'what this means', 'what it means'
    ]

    for w in noise_words:
        text = text.replace(w, ' ')

    text = re.sub(r'\s+', ' ', text).strip()
    return text

def contains_exact_term(text: str, term: str) -> bool:
    norm_text = normalize_text(text)
    norm_term = normalize_text(term)

    if not norm_term:
        return False

    pattern = rf'(^|\s){re.escape(norm_term)}($|\s)'
    return re.search(pattern, norm_text) is not None

def is_corporate_treasury_sale_article(text: str) -> bool:
    low = (text or "").lower()

    sale_terms = [
        'liquidates entire bitcoin stash',
        'bitcoin stash',
        'debt repayment',
        'repay debt',
        'sell bitcoin holdings',
        'liquidates holdings',
        '전량 매각',
        '비트코인 전량 매각',
        '부채 상환',
    ]

    company_terms = [
        'genius group', 'empery digital', 'treasury company',
        '지니어스그룹', '기업 재무', '재무 기업'
    ]

    return any(t in low for t in sale_terms) and any(t in low for t in company_terms)


def is_wallet_balance_metric_article(text: str) -> bool:
    low = (text or "").lower()

    wallet_terms = [
        'spendable wallets',
        'wallet balance',
        'held in wallets',
        'average holdings',
        'bag smashes',
        '보관 중임',
        '보유량',
        '평균 보유량',
        '지갑에 보관',
        '가용 지갑',
    ]

    xrp_terms = ['xrp', 'ripple', '리플']
    allow_terms = ['whale', '고래', 'santiment', '샌티먼트']
    if any(t in low for t in allow_terms):
        return False

    return any(t in low for t in wallet_terms) and any(t in low for t in xrp_terms)


def is_conference_opinion_article(text: str) -> bool:
    low = (text or "").lower()

    event_terms = [
        'conference', 'summit', 'forum', 'event', 'panel', 'speaker',
        'speaks on', 'spoke at', 'hosted by', 'co-hosted', 'presented by',
        'scheduled for', 'will be held', 'to be held', 'registration',
        '컨퍼런스', '서밋', '포럼', '행사', '이벤트', '패널', '연사',
        '개최', '개최됨', '열림', '주최', '공동 주최', '참가', '참여', '논의'
    ]

    promo_terms = [
        'eastpoint', 'hashed', 'bloomingbit', 'korea economic daily',
        'ticket', 'registration', 'attend', 'networking',
        'seoul 2026', 'september 28'
    ]

    hard_news_terms = [
        'approval', 'approved', 'license', 'licensed', 'bill', 'law',
        'launch', 'launched', 'lawsuit', 'settlement', 'etf',
        '승인', '인가', '법안', '출시', '소송', '합의'
    ]

    has_event = any(t in low for t in event_terms)
    has_promo = any(t in low for t in promo_terms)
    has_hard_news = any(t in low for t in hard_news_terms)

    return (has_event and not has_hard_news) or (has_promo and has_event) or ('challenge' in low) or ('campaign' in low)



def is_commentary_only_article(text: str) -> bool:
    low = (text or "").lower()

    # 말만 있고 실질 이벤트가 없는 표현
    commentary_terms = [
        'mentioned', 'mentions', 'noted', 'notes', 'explained', 'explains',
        'described', 'describes', 'highlighted', 'highlights',
        'commented', 'comments', 'said', 'says', 'stated', 'states',
        '언급함', '언급', '설명함', '설명', '강조함', '강조',
        '평가함', '평가', '말함', '밝힘', '전함', '묘사함', '묘사'
    ]

    # 진짜 뉴스로 볼 수 있는 실질 이벤트
    hard_news_terms = [
        'approved', 'approval', 'launched', 'launch', 'rolled out',
        'signed', 'agreement', 'partnership', 'integrated', 'integration',
        'licensed', 'license', 'lawsuit', 'settlement', 'filed',
        'passed', 'bill', 'act', 'law', 'policy change', 'adopted',
        '도입', '출시', '승인', '인가', '체결', '통합', '제휴',
        '소송', '합의', '통과', '법안', '시행', '정책 변경'
    ]

    has_commentary = any(t in low for t in commentary_terms)
    has_hard_news = any(t in low for t in hard_news_terms)

    # 설명형 문구가 있고, 실질 이벤트가 없으면 제외
    return has_commentary and not has_hard_news

def is_security_incident_article(text: str) -> bool:
    low = (text or "").lower()

    incident_terms = [
        'exploit', 'security incident', 'durable nonce',
        'unauthorized trade', 'unauthorized transfer',
        '익스플로잇', '보안 사고', '무단 거래 승인'
    ]

    return any(t in low for t in incident_terms)

def is_payment_adoption_article(text: str) -> bool:
    low = (text or "").lower()

    org_terms = [
        'bitget', 'etoro', 'kbank', '케이뱅크', '업비트',
        'bitlicense', 'card', 'payment', 'spending',
        'cross border', 'crossborder', '해외송금', '결제', '카드', '라이선스'
    ]

    positive_terms = [
        'launch', 'launched', 'wins', 'secured', 'obtained', 'expands',
        '출시', '획득', '확대', '도입', '활용'
    ]

    return any(t in low for t in org_terms) and any(t in low for t in positive_terms)


def is_exchange_mna_article(text: str) -> bool:
    low = (text or "").lower()

    exchange_terms = [
        'coinone', 'korbit', 'exchange stake', 'stake acquisition',
        '지분 인수', '인수 검토', '거래소 지분', '코인원', '코빗'
    ]

    finance_terms = [
        'korea investment', 'mirae asset', '한국투자증권', '미래에셋'
    ]

    return any(t in low for t in exchange_terms) and any(t in low for t in finance_terms)



ENTITY_TRANSLATION_MAP = dict(MANUAL_TRANSLATIONS)

STRICT_ALLOWED_ASSETS = [
    'bitcoin', 'btc', 'ethereum', 'eth', 'xrp', 'ripple', 'xlm', 'stellar',
    'ada', 'cardano', 'trx', 'tron', 'bnb', 'bch', 'bitcoin cash',
    'shib', 'shiba inu', 'etc', 'flr', 'athena', 'ena', 'usdc', 'usdt',
    '비트코인', '이더리움', '리플', '스텔라', '에이다', '트론',
    '바이낸스코인', '비트코인캐시', '시바이누', '플레어', '에테나',
]

STRICT_CRYPTO_CONTEXT = [
    '암호화폐', '가상자산', '디지털자산', '블록체인',
    'crypto', 'cryptocurrency', 'digital asset', 'digital assets', 'blockchain',
    'etf', 'stablecoin', 'custody', 'tokenization', 'wallet', 'exchange',
    '수탁', '토큰화', '지갑', '거래소', '스테이블코인',
]

STRICT_POLICY_CONTEXT = [
    'sec', 'cftc', 'occ', 'fed', 'treasury', 'senate', 'house', 'committee',
    'regulation', 'regulated', 'bill', 'law', 'act', 'policy', 'approval',
    '승인', '규제', '법안', '정책', '상원', '하원', '위원회', '연준', '재무부',
]

TAG_PARTICLES = [
    '으로', '에서', '에게', '까지', '부터',
    '은', '는', '이', '가', '을', '를', '의', '와', '과', '로', '도', '만',
]

def _contains_any_term(text: str, terms: list[str]) -> bool:
    if not text or not terms:
        return False
    low = normalize_for_duplicate(str(text))
    for term in terms:
        if not term:
            continue
        t = normalize_for_duplicate(str(term))
        if not t:
            continue
        if contains_exact_term(low, t):
            return True
    return False

def _entity_korean_name_strict(entity: str, context_text: str = "") -> str:
    if not entity:
        return ""
    ent = str(entity).strip()
    if not ent:
        return ""

    if ent in {"Gold", "금"} and not has_precious_metal_context(context_text, "gold"):
        return ""
    if ent in {"Silver", "은"} and not has_precious_metal_context(context_text, "silver"):
        return ""

    if ent in ENTITY_TRANSLATION_MAP:
        mapped = ENTITY_TRANSLATION_MAP[ent]
    else:
        mapped = entity_korean_name(ent)

    mapped = str(mapped).strip().replace(" ", "")
    if mapped == "금" and not has_precious_metal_context(context_text, "gold"):
        return ""
    if mapped == "은" and not has_precious_metal_context(context_text, "silver"):
        return ""
    return mapped

def _is_inline_tag_candidate(tag_name: str, text: str = "") -> bool:
    if not tag_name:
        return False
    if tag_name in ALWAYS_INLINE_TAGS or tag_name in INLINE_TAG_WHITELIST:
        return True
    return len(tag_name) >= 2 and tag_name in (text or "")


def matches_keywords(story: dict, coins: list[str], econ_keywords: list[str], korean_keywords: list[str]) -> bool:
    raw_text = (story.get('title', '') + ' ' + story.get('desc', '')).strip()
    raw_lower = raw_text.lower()
    url = (story.get('url', '') or '').lower()

    direct_chart_terms = [
        'oversold', 'overbought', 'rebound', '70k', 'what next', 'next?', 'can btc',
        'price analysis', 'technical analysis', 'price prediction', 'forecast',
        'support', 'resistance', 'breakout', 'trend line', 'target price',
        '과매도', '과매수', '반등', '기술적 분석', '차트 분석', '목표가', '지지선', '저항선'
    ]
    if '/markets/' in url and any(term in raw_lower for term in direct_chart_terms):
        print(f"[차트/가격형 URL 제외] {story.get('title', '')}")
        return False

    portfolio_context_terms = [
        'bitcoin', 'btc', 'ethereum', 'eth', 'xrp', 'ripple', 'xlm', 'stellar',
        'ada', 'cardano', 'trx', 'tron', 'bnb', 'bch', 'bitcoin cash',
        'shib', 'shiba inu', 'etc', 'flr', 'athena', 'ena', 'usdc', 'usdt',
        '비트코인', '이더리움', '리플', '스텔라', '에이다', '트론',
        '바이낸스코인', '비트코인캐시', '시바이누', '플레어', '에테나'
    ]

    ai_company_terms = [
        'openai', 'anthropic', 'google', 'block', 'ai',
        'middle management', 'organization design', '업무 환경', '조직', 'ai'
    ]

    if 'tokenpost.kr/news/tech/' in url:
        return False

    hard_irrelevant_terms = ['moew', 'realgo', 'fast or go home', 'allunity', 'kalqix', 'kalaix', 'challenge', 'mainnet launch', 'clob dex', 'agent', 'airdrop', 'launch campaign', 'wallet campaign']
    if any(t in raw_lower for t in hard_irrelevant_terms):
            print(f"[홍보/비관련 제외] {story.get('title', '')}")
            return False

       # 1. 기본 네거티브 차단
    for neg in NEGATIVE_KEYWORDS:
        if neg.lower() in raw_lower:
            print(f"[NEGATIVE 제외] {story.get('title', '')} / {neg}")
            return False

    if contains_bad_signal(raw_text):
        print(f"[부정시그널 제외] {story.get('title', '')}")
        return False

    if is_corporate_treasury_sale_article(raw_text):
        print(f"[기업재무매각 제외] {story.get('title', '')}")
        return False

    if is_wallet_balance_metric_article(raw_text):
        print(f"[지갑보유량 제외] {story.get('title', '')}")
        return False

    if is_conference_opinion_article(raw_text):
        print(f"[행사발언 제외] {story.get('title', '')}")
        return False

    if is_commentary_only_article(raw_text):
        print(f"[설명형/코멘트형 제외] {story.get('title', '')}")
        return False

    if is_security_incident_article(raw_text):
        print(f"[보안사고 제외] {story.get('title', '')}")
        return False

    # 2. 차트/가격형 기사 차단
    if is_chart_or_price_article(raw_text):
        print(f"[차트/가격형 제외] {story.get('title', '')}")
        return False

    # 3. 포트폴리오 외 코인 차단
    allowed_coin_found = any(contains_exact_term(raw_text, c) for c in coins)
    if not allowed_coin_found and contains_non_portfolio_asset(raw_text):
        print(f"[포폴외코인 제외] {story.get('title', '')}")
        return False

    # 4. 일반 주식 문맥 차단
    if contains_stock_context(raw_text) and not allowed_coin_found:
        print(f"[주식기사 제외] {story.get('title', '')}")
        return False

    # 5. 나머지 BAD_TOPIC 차단
    if contains_bad_topic(raw_text):
        print(f"[주제제외] {story.get('title', '')}")
        return False

    # 6. 허용 코인 직접 등장 기사
    if allowed_coin_found:
        print(f"[허용코인 통과] {story.get('title', '')}")
        return True

    # 7. 순수 거시/정책 기사 허용
    if is_pure_macro_article(raw_text):
        print(f"[거시/정책 통과] {story.get('title', '')}")
        return True

    # 8. XRP 서사형 기사 허용
    if is_xrp_narrative_article(raw_text):
        print(f"[XRP서사 통과] {story.get('title', '')}")
        return True

    # 9. AI/기업 기사 허용
    if any(contains_exact_term(raw_text, t) for t in ai_company_terms):
        print(f"[AI/기업기사 통과] {story.get('title', '')}")
        return True

    if is_payment_adoption_article(raw_text):
        print(f"[결제/채택 통과] {story.get('title', '')}")
        return True

    if is_exchange_mna_article(raw_text):
        print(f"[거래소M&A 통과] {story.get('title', '')}")
        return True

    print(f"[필터미통과] {story.get('title', '')}")
    return False

def is_canonical_duplicate(canonical_key: str, seen_keys: set[str]) -> bool:
    if not canonical_key:
        return False

    current = {x.strip() for x in canonical_key.split('|') if x.strip()}

    for old_key in seen_keys:
        old = {x.strip() for x in old_key.split('|') if x.strip()}
        shared = current & old

        if len(shared) >= 4:
            log(f"[정규토픽중복 제외] shared={shared}")
            return True

        if len(current) >= 4 and len(old) >= 4 and len(shared) >= min(len(current), len(old)) - 1:
            log(f"[정규토픽유사 제외] shared={shared}")
            return True

    return False
	
def is_bad_line(line: str) -> bool:
    low = line.lower().strip()
    return (not low) or ('visit website' in low) or ('웹사이트 방문' in low) or ('?' in line) or ('？' in line) or bool(re.fullmatch(r'https?://\S+', low))

def score_sentence(s: str, title: str = "") -> int:
    low = s.lower()
    score = 0

    important_terms = [
        'bitcoin', 'btc', 'ethereum', 'eth', 'xrp', 'ripple',
        'etf', 'sec', 'fed', 'inflation', 'interest rate',
        'stablecoin', 'tokenization', 'lawsuit', 'approval',
        'exchange', 'binance', 'coinbase', 'blackrock'
    ]

    for term in important_terms:
        if term in low:
            score += 3

    if re.search(r'\d', s):
        score += 2

    if len(s) < 25:
        score -= 1
    if len(s) > 140:
        score -= 1

    title_words = set(re.findall(r'[A-Za-z0-9가-힣]+', title.lower()))
    sent_words = set(re.findall(r'[A-Za-z0-9가-힣]+', low))
    score += len(title_words & sent_words)

    if 'according to' in low or 'first appeared' in low:
        score -= 5

    return score

def has_weak_reference(text: str) -> bool:
    low = f" {text.lower()} "
    weak_refs = [
        ' it ', ' they ', ' them ', ' this ', ' that ', ' these ', ' those ',
        ' its ', ' their ', ' his ', ' her ',
        '그것', '그들이', '그들', '이는', '이것', '저것', '해당', '이를', '그의', '그녀의'
    ]
    return any(x in low for x in weak_refs)

def summarize_text(text: str, title: str = "", max_sentences: int = 3) -> str:
    text = cleanup_text(text)
    title = cleanup_text(title)

    if is_weak_text(text):
        text = title

    raw_sentences = re.split(r'(?<=[.!?])\s+|\n+|(?<=다)\s+|(?<=임)\s+|(?<=음)\s+', text)

    indexed_sentences = []
    for idx, s in enumerate(raw_sentences):
        s = s.strip(" ,")
        if not s or is_bad_line(s):
            continue
        indexed_sentences.append((idx, s))

    if not indexed_sentences:
        return title

    ranked = sorted(
        indexed_sentences,
        key=lambda x: score_sentence(x[1], title),
        reverse=True
    )

    picked = []
    picked_idx = set()
    total_len = 0
    max_len = 180

    for idx, s in ranked:
        candidates = []

        if has_weak_reference(s) and idx > 0:
            prev_s = raw_sentences[idx - 1].strip(" ,")
            if prev_s and not is_bad_line(prev_s):
                candidates.append((idx - 1, prev_s))

        candidates.append((idx, s))

        stop_outer = False

        for cand_idx, cand_s in candidates:
            if cand_idx in picked_idx:
                continue

            if total_len + len(cand_s) > max_len and picked:
                stop_outer = True
                break

            picked.append((cand_idx, cand_s))
            picked_idx.add(cand_idx)
            total_len += len(cand_s)

            if len(picked) >= max_sentences:
                stop_outer = True
                break

        if stop_outer:
            break

    if not picked:
        return title

    picked.sort(key=lambda x: x[0])
    summary = ' '.join(s for _, s in picked)
    summary = re.sub(r'\s+', ' ', summary).strip()
    return summary

def translate_text_to_korean(text: str) -> str:
    if not text:
        return ""
    try:
        from googletrans import Translator  # type: ignore
        translator = Translator()
        result = translator.translate(text, dest='ko')
        if iscoroutine(result):
            result = asyncio.run(result)
        return result.text
    except Exception:
        try:
            from googletrans import Translator  # type: ignore
            async def _translate(src: str) -> str:
                async with Translator() as trans:
                    r = await trans.translate(src, dest='ko')
                    return r.text
            return asyncio.run(_translate(text))
        except Exception:
            return text

def normalize_style(text: str) -> str:
    rules = [
        (r'사용됩니다\.?', '사용됨'),
        (r'있습니다\.?', '있음'),
        (r'내렸다\.?', '내림'),
        (r'늘렸습니다\.?', '늘림'),
        (r'불러일으킵니다\.?', '불러일으킴'),
        (r'미칩니다\.?', '미침'),
        (r'나타냅니다\.?', '나타냄'),
        (r'했습니다\.?', '함'),
        (r'하였습니다\.?', '함'),
        (r'합니다\.?', '함'),
        (r'하고 있습니다\.?', '하고 있음'),
        (r'하고 있다\.?', '하고 있음'),
        (r'기록했습니다\.?', '기록'),
        (r'승인했습니다\.?', '승인'),
        (r'였습니다\.?', '임'),
        (r'입니다\.?', '임'),
        (r'이었습니다\.?', '임'),
        (r'이다\.?', '임'),
        (r'습니다\.?', '음'),
        (r'알려졌습니다\.?', '알려짐'),
        (r'알려졌다\.?', '알려짐'),
        (r'밀렸다\.?', '밀림'),
        (r'밀렸습니다\.?', '밀림'),
        (r'됐다\.?', '됨'),
        (r'알려졌습니다\.?', '알려짐'),
        (r'졌다\.?', '졌음'),
        (r'됩니다\.?', '됨'),
        (r'있다\.?', '있음'),
		(r'밝혔다\.?', '밝힘'),
        (r'전했다\.?', '전함'),
        (r'설명했다\.?', '설명함'),
        (r'덧붙였다\.?', '덧붙임'),
    ]

    leftovers = re.findall(r'[\w가-힣]+(?:했습니다|하였습니다|합니다|있습니다|됩니다|나타냅니다|미칩니다)', text)
    if leftovers:
        log("말투 치환 추가 필요 후보: " + ", ".join(leftovers[:10]))

    for pat, rep in rules:
        text = re.sub(pat, rep, text)

    text = re.sub(r'\[\.\.\.\]|\.\.\.|…', ' ', text)
    text = re.sub(r'\s*:\s*\[\s*\]', ' ', text)
    text = re.sub(r'([가-힣])([A-Z][a-zA-Z]+)', r'\1 \2', text)
    text = re.sub(r'\s+', ' ', text).strip()

    text = re.sub(r'([가-힣]+)음고 말함', r'\1음', text)
    text = re.sub(r'([가-힣]+)음고 밝힘', r'\1음', text)
    text = re.sub(r'([가-힣]+)다고 말함', r'\1', text)
    text = re.sub(r'([가-힣]+)다고 밝힘', r'\1', text)
    text = re.sub(r'([가-힣]+)라고 말함', r'\1', text)
    text = re.sub(r'([가-힣]+)라고 밝힘', r'\1', text)
    text = re.sub(r'했다고 말함$', '했음', text)
    text = re.sub(r'했다고 밝힘$', '했음', text)
    text = re.sub(r'했다고 전함$', '했음', text)
    text = re.sub(r'이어질 것으로 봄고 말함$', '이어질 것으로 봄', text)

    return text

def fix_truncated_phrases(text: str) -> str:
    fixes = {
        'USDC는': 'USDC는 전송량 경쟁 구도 변화의 중심에 섬',
        '잡담이': '관련 논의도 이어지는 중',
        '공급을': '공급 확대 흐름도 이어지는 중',
        'JPMorgan은 또한 일부 민간 신용을 인하함': 'JPMorgan은 일부 민간 신용도 함께 인하',
        '위태로운 것은 달러 연계 여부이다': '핵심 변수는 달러 연계 유지 여부로 좁혀짐',
    }
    for k, v in fixes.items():
        text = re.sub(r'\b' + re.escape(k), v, text)
    text = re.sub(r'\[\.\.\.\]|\.\.\.|…', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text



def extract_entities(story: dict, max_tags: int = 8) -> list[str]:
    title = story.get('title', '')
    desc = story.get('desc', '')
    text = title + " " + desc
    entities = []

    for key in sorted(MANUAL_TRANSLATIONS.keys(), key=len, reverse=True):
        if re.search(r'\b' + re.escape(key) + r'\b', text, re.I):
            entities.append(key)

    for kw in KOREAN_TAG_KEYWORDS:
        # 금/은은 직접 포함 검사 금지
        if kw in {'금', '은'}:
            continue
        if kw in text:
            entities.append(kw)

    # gold/silver는 영어 문맥일 때만 수동 추가
    if has_precious_metal_context(text, 'gold'):
        entities.append('Gold')
    if has_precious_metal_context(text, 'silver'):
        entities.append('Silver')

    for coin in PORTFOLIO_COINS:
        if re.search(r'\b' + re.escape(coin) + r'\b', text, re.I):
            entities.append(coin)

    grouped = re.findall(r'\b(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3}|[A-Z]{2,6})\b', title)
    for token in grouped:
        if token in SITE_NAMES or token.lower() in {w.lower() for w in IGNORED_WORDS}:
            continue
        entities.append(token)

    seen = set()
    result = []
    for ent in entities:
        k = ent.lower()
        if k not in seen:
            result.append(ent)
            seen.add(k)

    result.sort(key=lambda e: text.lower().find(e.lower()) if text.lower().find(e.lower()) >= 0 else 99999)
    return result[:max_tags]

def extract_entities_from_summary(summary: str, max_tags: int = 8) -> list[str]:
    text = summary or ""
    entities = []

    for key in sorted(MANUAL_TRANSLATIONS.keys(), key=len, reverse=True):
        if re.search(r'\b' + re.escape(key) + r'\b', text, re.I):
            entities.append(key)

    for kw in KOREAN_TAG_KEYWORDS:
        if kw in {'금', '은'}:
            continue
        if re.search(r'\b' + re.escape(kw) + r'\b', text, re.I):
            entities.append(kw)

    for coin in PORTFOLIO_COINS:
        if re.search(r'\b' + re.escape(coin) + r'\b', text, re.I):
            entities.append(coin)

    seen = set()
    result = []
    for ent in entities:
        k = ent.lower()
        if k not in seen:
            result.append(ent)
            seen.add(k)

    result.sort(key=lambda e: text.lower().find(e.lower()) if text.lower().find(e.lower()) >= 0 else 99999)
    return result[:max_tags]

def entity_korean_name(entity: str) -> str:
    if entity in MANUAL_TRANSLATIONS:
        return MANUAL_TRANSLATIONS[entity]
    return entity.replace(' ', '')

def inject_entity_hashtags(summary: str, entities: list[str]) -> tuple[str, list[str]]:
    text = summary
    final_tags = []

    coin_inline_map = {
        'BTC': '비트코인',
        'ETH': '이더리움',
        'XRP': 'XRP',
        'XLM': '스텔라',
        'ADA': '에이다',
        'TRX': '트론',
        'BNB': '바이낸스',
        'BCH': '비트코인캐시',
        'SHIB': '시바이누',
        'USDC': 'USDC',
        'USDT': 'USDT',
    }

    for ent in sorted(entities, key=len, reverse=True):
        ent_upper = ent.upper()

        if ent_upper in PORTFOLIO_COINS or ent_upper in CRYPTO_ACRONYMS:
            if f'#{ent_upper}' not in final_tags:
                final_tags.append(f'#{ent_upper}')

            korean_name = coin_inline_map.get(ent_upper, ent_upper)
            tag_text = f'#{korean_name}'

            if tag_text in text:
                continue

            replaced = False
            for base in [korean_name, ent, ent_upper]:
                for p in ['가','이','은','는','를','을','의','와','과','로','도','만','에서','에게','까지']:
                    new_text, count = re.subn(re.escape(base + p), f'{tag_text} {p}', text, count=1)
                    if count:
                        text = new_text
                        replaced = True
                        break
                if replaced:
                    break

            if not replaced:
                for base in [korean_name, ent, ent_upper]:
                    new_text, count = re.subn(re.escape(base), tag_text, text, count=1)
                    if count:
                        text = new_text
                        break

            continue

        korean = entity_korean_name(ent)
        tag_text = '#' + korean.replace(' ', '')
        eng_tag = '#' + ent.replace(' ', '')
        if eng_tag not in final_tags:
            final_tags.append(eng_tag)

        normalized_korean_tag = '#' + korean.replace(' ', '')
        normalized_eng_tag = '#' + ent.replace(' ', '')

        if normalized_korean_tag in text or normalized_eng_tag in text:
            continue

        replaced = False
        for base in [korean, ent]:
            for p in ['가','이','은','는','를','을','의','와','과','로','도','만','에서','에게','까지']:
                new_text, count = re.subn(re.escape(base + p), f'{tag_text} {p}', text, count=1)
                if count:
                    text = new_text
                    replaced = True
                    break
            if replaced:
                break

        if not replaced:
            for base in [korean, ent]:
                new_text, count = re.subn(re.escape(base), tag_text, text, count=1)
                if count:
                    text = new_text
                    break

    return text, final_tags

def fix_broken_inline_hashtags(text: str) -> str:
    text = re.sub(r'#+', '#', text)
    text = re.sub(r'#\s+', '#', text)

    # 정말 깨진 해시태그만 수동 복구
    text = text.replace('#미 국', '#미국')
    text = text.replace('#비트 코 인', '#비트코인')
    text = text.replace('#이더 리 움', '#이더리움')
    text = text.replace('#시 바 이 누', '#시바이누')
    text = text.replace('#신 시 아 루 미 스', '#신시아루미스')
    text = text.replace('#마이클#세일러', '#마이클세일러')
    text = text.replace('#브래드#갈링하우스', '#브래드갈링하우스')
    text = text.replace('#토비아스#아드리안', '#토비아스아드리안')
    text = text.replace('#R L U S D', '#RLUSD')
    text = text.replace('RL#미국D', '#RLUSD')
    text = text.replace('#엑스알피', '#XRP')
    text = text.replace('#리플 ', '#XRP ')
    text = text.replace('#리플\n', '#XRP\n')
    text = text.replace('#F O M C', '#FOMC')
    text = text.replace('#헤스터 피어스', '#헤스터피어스')
    text = text.replace('#리플', '#XRP')
    text = text.replace('#X R P', '#XRP')
    text = text.replace('#F O M C', '#FOMC')
    text = text.replace('#시카고상품거래소', '#시카고상품거래소(CME)')
    text = text.replace('#Qivalis', '#키발리스')
    text = text.replace('#Nuva', '#누바')
    text = text.replace('#Tempo', '#템포')
    text = text.replace('#MoneyGram', '#머니그램')
    text = text.replace('#Muro', '#무로')
    text = text.replace('#Santander', '#산탄데르')

    return text


def remove_duplicate_inline_hashtags(text: str) -> str:
    seen = set()

    def repl(match):
        tag = match.group(0)
        key = tag.lower()
        if key in seen:
            return ''
        seen.add(key)
        return tag

    text = re.sub(r'#[가-힣A-Za-z0-9]+', repl, text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def cleanup_text(text: str) -> str:
    text = re.sub(r'@([A-Za-z0-9_\.]+)', r'\1', text)

    bad_phrases = [
        '다음 기사는',
        '뉴스레터',
        '발췌한 것임',
        '[]로 시작됩니다',
        '[]를 제외하고',
        '[]'
    ]

    for p in bad_phrases:
        text = text.replace(p, '')

    text = re.sub(r'.*?Crypto Briefing에 처음 등장(?:함|했다)\.?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'.*?크립토 브리핑\(Crypto Briefing\)에 처음 등장(?:함|했다)\.?', '', text)
    text = re.sub(r'.*?Crypto Briefing에 처음 게재되(?:었음|었다|었습니?다)\.?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'.*?크립토 브리핑\(Crypto Briefing\)에 처음 게재되(?:었음|었다|었습니?다)\.?', '', text)

    text = re.sub(r'.*?first appeared on.*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'.*?처음 게재되(?:었|었습|었음).*', '', text)
    text = re.sub(r'.*?Times Tabloid에 처음 게재되(?:었|었습|었음).*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'.*?TimesTabloid에 처음 게재되(?:었|었습|었음).*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'코인데스크에 따르면[, ]*', '', text, flags=re.I)
    text = re.sub(r'cryptonews\s*에?\s*처음 등장함', '', text, flags=re.I)
    text = re.sub(r'crypto\s*biz:\s*', '', text, flags=re.I)

    text = text.replace('포스트가 ', '')
    text = text.replace('게시물이 ', '')
    text = text.replace('게재물이 ', '')
    text = text.replace('라는 포스트가 ', '')
    text = text.replace('라는 게시물이 ', '')

    text = re.sub(r'^[^.!?\n]{0,40}에 따르면[, ]*', '', text)
    text = re.sub(r'본 콘텐츠는 특정 종목이나 자산에 대한 투자 조언이 아니며[^.!?\n]*', '', text)
    text = re.sub(r'변동성 높은 시장에서 흔들리지 않는 투자 마인드를 가꾸기 위한 심리적 환기 목적으로 제공됩니다[^.!?\n]*', '', text)

    text = re.sub(r'\s+', ' ', text).strip()
    return text


def fix_translation_terms(text: str) -> str:
    replacements = {
    '401(k)': '401k',
    '401 k': '401k',
    '401K': '401k',
    'U.S. Department of Labor': '미국 노동부',
    'US Department of Labor': '미국 노동부',
    'Department of Labor': '노동부',
    'Labor Department': '노동부',
    'Bitcoin Cash': '비트코인캐시',
	'클레러티법': '클래리티법',
    '클레리티법': '클래리티법',
    '클레러티': '클래리티',
    '클레리티': '클래리티',
		'Shiba Inu': '시바이누',
'shiba inu': '시바이누',
'시바견': '시바이누',
		'시토시': '사토시',
'사토시 쿠사마': '사토시쿠사마',
'Satoshi Kusama': '사토시쿠사마',
    'XRP Ledger': 'XRPLedger',
    'xrp ledger': 'XRPLedger',
    'RLUSD': 'RLUSD',
    'FOMC': 'FOMC',
    'Hester Peirce': '헤스터피어스',
    'CME Group': '시카고상품거래소(CME)',
    'Chicago Mercantile Exchange': '시카고상품거래소(CME)',
    'Qivalis': '키발리스',
    'Raoul Pal': '라울팔',
    'NUVA': '누바',
    'Tempo': '템포',
    'MoneyGram': '머니그램',
    'MiCA': '미카',
    'MICA': '미카',
    'AllUnity': '올유니티',
    'Kalqix': '칼릭스',
    'KalaiX': '칼릭스',
    'Truth Social': '트루스소셜',
    'Tohoku Bank': '도호쿠은행',
    'SBI Remit': 'SBIRemit',
    'SoftBank': '소프트뱅크',
    'Twenty One Capital': '트웬티원캐피털',
    'Timothy Massad': '티머시매사드',
    'Santiment': '샌티먼트',
    'Santander': '산탄데르',

    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r'\[\.\.\.\]|\.\.\.|…', ' ', text)
    text = re.sub(r'\s*:\s*\[\s*\]', ' ', text)
    text = re.sub(r'[ \t]+', ' ', text).strip()

    return text

def filter_final_tags(tags: list[str]) -> list[str]:
    allowed_exact = {
        '#BTC','#ETH','#XRP','#XLM','#ADA','#TRX','#BNB','#BCH','#SHIB','#ETC','#FLR','#ATHENA','#ETNA','#USDC','#USDT',
        '#Ripple','#Ethereum','#Bitcoin','#Stablecoin','#DeFi','#NFT','#Web3',
        '#ETF','#SEC','#CFTC','#OCC','#IPO','#CTO','#AI',
        '#JPMorgan','#MorganStanley','#GoldmanSachs','#BlackRock','#Coinbase','#Binance','#Upbit','#Bithumb',
        '#OpenAI','#Anthropic','#Google','#Apple','#PayPal','#Stripe','#Microsoft',
        '#DavidSchwartz','#BradGarlinghouse','#MonicaLong','#MichaelSaylor','#JeromePowell',
        '#TomLee','#JackDorsey','#PaulGrewal','#MichaelBarr','#MichaelSelig',
        '#Tether','#Circle','#MoneyGram','#Mastercard','#Visa',
        '#Metaplanet','#Strategy','#Robinhood','#Kraken','#WellsFargo',
        '#FranklinTempleton','#TonyPecore','#WisdomTree',
        '#GeniusGroup','#GENIUS','#CLARITY','#CLARITYAct',
        '#KBank','#Coinone','#Bitget','#SafePal','#eToro','#HKMA','#HSBC','#StandardChartered',
        '#US','#Korea','#Japan','#China','#Taiwan','#HongKong','#Australia','#Brazil','#India','#Iran','#Israel','#Qatar',
        '#XRPLedger','#BitMine','#BCH','#TRON','#TRX','#XAUT','#SHIB','#XRP','#XLM','#XRPL', '#DEX', '#DeFi','#Bitdeer','#Blockstream',
        '#FOMC','#RLUSD','#시카고상품거래소','#키발리스','#라울팔','#누바','#템포','#머니그램','#미카','#도호쿠은행','#SBIRemit','#소프트뱅크','#트웬티원캐피털','#화이트비트','#티머시매사드','#무로','#산탄데르',
		'#IMF', '#TobiasAdrian', '#RWA', '#GENIUSAct','#Oracle','#Coinone', '#Korea', '#Japan', '#BankOfJapan', '#BankOfKorea',
'#IMF', '#ABA', '#RWA', '#CBDC',
'#MonicaLong', '#ODL', '#FedNow', '#Fedwire',
'#AndrewBailey', '#HyunSongShin',
'#Metaplanet', '#Upbit',
'#BradGarlinghouse', '#CLARITY', '#CLARITYAct',
'#PeterSchiff', '#Gold', '#Silver',
'#CharlesSchwab', '#Oracle',
'#JeffPark', '#ProCap',
    }

    allowed_exact |= COUNTRY_FINAL_TAGS

    blocked_contains = [
        'Highlights','Surprise','Underpriced','Needs','Run','Hitting','Fall',
        'Mean','Errors','Peak','Insufficient','Deals','Game','Escrow','Top',
        'Early','About','What','Will','Passes','Says','This','Hard',
        'Level','Trigger','Million','Long','Squeeze','Could'
    ]

    cleaned = []
    for tag in tags:
        tag = tag.replace('.', '')

        # footer에는 한글 해시태그 금지
        if re.search(r'#[가-힣]+', tag):
            continue

        if any(b.lower() in tag.lower() for b in blocked_contains):
            continue

        if tag in allowed_exact:
            cleaned.append(tag)

    return list(dict.fromkeys(cleaned))


def fetch_article_text(url: str) -> str:
    try:
        html_text = http_get(url, timeout=10)
    except Exception:
        return ""

    patterns = [
        r'<article[^>]*>(.*?)</article>',
        r'<main[^>]*>(.*?)</main>',
        r'<body[^>]*>(.*?)</body>',
    ]

    block = ""
    for pat in patterns:
        m = re.search(pat, html_text, re.I | re.S)
        if m:
            block = m.group(1)
            break

    if not block:
        block = html_text

    paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', block, re.I | re.S)
    cleaned = []
    for p in paragraphs:
        t = re.sub(r'<[^>]+>', ' ', unescape(p))
        t = re.sub(r'\s+', ' ', t).strip()
        if len(t) >= 40:
            cleaned.append(t)

    text = "\n".join(cleaned[:20]).strip()
    text = cleanup_text(text)
    return text[:12000]

def get_best_source_text(story: dict) -> str:
    article_text = fetch_article_text(story.get('url', ''))
    desc = (story.get('desc') or '').strip()
    title = (story.get('title') or '').strip()

    if article_text and len(article_text) >= 180:
        return article_text
    if desc and len(desc) >= 80:
        return desc
    return title


def rewrite_summary_with_gemini(title: str, article_text: str, fallback_text: str = "") -> str:
    source_text = (article_text or "").strip()
    if not source_text:
        source_text = (fallback_text or "").strip()
    if not source_text:
        source_text = title.strip()

    if not openai_client:
        return ""

    try:
        prompt = f"""
너는 텔레그램 암호화폐 뉴스 채널 편집자다.

아래 기사 내용을 보고 한국어로 자연스럽게 2~3문장으로 다시 써라.

규칙:
- 텔레그램 업로드용 짧은 문장으로 작성
- 첫 문장부터 핵심 키워드를 강하게 시작(느낌표 물음표는 사용금지)
- 해시태그는 마지막 footer에서만 사용됨
- 사람 이름, 기관명, 코인명도 일반 텍스트로 자연스럽게 작성
- 해시태그 사용하면 띄어쓰기 필수
- 한국어 띄어쓰기를 자연스럽게 유지
- 반드시 2~3문장만 작성
- 각 문장은 짧게 작성
- 한 문장이 끝날 때마다 반드시 한 줄 띄울 것
- 전체 길이는 160~220자 이내로 유지하되, 문장이 중간에 끊기지 않게 완성할 것
- 불필요한 배경 설명 금지
- 문장 끝은 텔레그램 축약형으로 정리할 것 (예: 밝혔다→밝힘, 전했다→전함, 설명했다→설명함)
- 필요하면 불릿(- 또는 ➖) 사용 가능
- 너무 딱딱한 기사체보다, 빠르게 읽히는 텔레그램 뉴스 톤으로 작성
- 직역투 금지
- 기사에 없는 내용은 추측해서 추가 금지
- 매체명, first appeared on, sponsor 문구 제거
- 문장은 너무 길지 않게 끊되, 의미가 빠지거나 중간에서 끝난 느낌이 나면 안 됨
- 출력은 요약문만 작성
- 마지막 해시태그 줄, 출처, 링크 문구는 작성하지 말 것
- 사람 이름, 국가명, 브랜드명, 코인명은 중간 띄어쓰기 없이 자연스럽게 작성
- 해시태그 내부 단어를 분리하지 말 것
- 본문에는 해시태그를 넣지 말 것
- 아래 표현은 절대 쓰지 말 것:
  하락세, 약세, 급락, 반등 실패, 상승으로 이어지지 못함, 강세 전환 신호 없음, 불확실, 이유, 전망, 크로스오버
- 가격 차트 해설 기사나 기술적 분석 기사처럼 보이면 빈 문자열만 반환할 것
- 롱/숏/청산/시장심리/챌린지/광고성 캠페인/에어드롭/메인넷 출시 홍보처럼 보이면 빈 문자열만 반환할 것
- 인물명, 기관명, 국가명, 법안명은 기사에 있으면 요약문 본문에 가능한 한 직접 1회 포함할 것
- 예: Michael Barr, GENIUS Act, Australia, Hong Kong, HKMA, HSBC, Standard Chartered

제목:
{title}

본문:
{source_text}
""".strip()

        response = openai_client.responses.create(
            model=OPENAI_MODEL,
            input=prompt,
        )

        text = (response.output_text or "").strip()
        text = cleanup_text(text)
        text = fix_translation_terms(text)
        text = fix_truncated_phrases(text)
        text = normalize_style(text)
        text = cleanup_text(text)
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text).strip()

        if is_refusal_or_skip_text(text):
            log(f"[요약거부/스킵 감지] {title}")
            return ""

        log_openai_cost(title, prompt, text)
        return text

    except Exception as e:
        log(f"OpenAI 요약 실패: {e}")
        return ""

def normalize_for_duplicate(text: str) -> str:
    text = text.lower()

    noise_words = [
        'says', 'said', 'claims', 'claim', 'predicts', 'predict', 'analyst', 'analysts',
        'expert', 'experts', 'report', 'reports', 'reported',
        'according to', 'could', 'may', 'might', 'will',
        'price prediction', 'forecast', 'outlook',
        'surges', 'jumps', 'rises', 'falls', 'drops',
        'here is', 'here’s', 'what this means', 'what it means'
    ]

    for w in noise_words:
        text = text.replace(w, ' ')

    text = re.sub(r'https?://\S+', ' ', text)
    text = re.sub(r'[^a-z0-9가-힣\s]', ' ', text)
    text = text.replace('ripple', 'xrp')
    text = text.replace('cme group', 'cme')
    text = text.replace('chicago mercantile exchange', 'cme')
    text = text.replace('hester peirce', '헤스터피어스')
    text = text.replace('qivalis', '키발리스')
    text = text.replace('nuva', '누바')
    text = text.replace('tempo', '템포')
    text = text.replace('moneygram', '머니그램')
    text = text.replace('raoul pal', '라울팔')
    text = text.replace('muro', '무로')
    text = text.replace('santander', '산탄데르')
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def build_canonical_topic_key(story: dict) -> str:
    text = normalize_for_duplicate(f"{story.get('title', '')} {story.get('desc', '')}")
    parts = []

    # 지역 / 국가
    geo_map = {
        '미국': ['united states', 'us', 'u s', 'america', '미국'],
        '호주': ['australia', 'australian', '호주'],
        '홍콩': ['hong kong', '홍콩'],
        '이란': ['iran', '이란'],
        '일본': ['japan', '일본'],
        '한국': ['korea', 'south korea', '한국'],
        '중국': ['china', '중국'],
        '유럽': ['eu', 'europe', 'european union', '유럽'],
        '영국': ['uk', 'united kingdom', 'britain', '영국'],
        '독일': ['germany', '독일'],
        '이탈리아': ['italy', '이탈리아'],
    }

    for key, terms in geo_map.items():
        if any(contains_exact_term(text, t) for t in terms):
            parts.append(f'geo_{key}')

    # 자산 / 핵심 주제
    topic_map = {
        '비트코인': ['bitcoin', 'btc', '비트코인'],
        '이더리움': ['ethereum', 'eth', '이더리움'],
        '리플': ['xrp', 'ripple', 'xrpl', 'xrp ledger', '리플'],
        '스테이블코인': ['stablecoin', '스테이블코인'],
        'etf': ['etf'],
        '라이선스': ['license', 'licensing', 'licensed', '라이선스'],
        '법안': ['bill', 'law', 'act', '법안'],
        '규제': ['regulation', 'regulatory', 'regulated', '규제'],
        '연준': ['fed', 'federal reserve', '연준'],
        '청문회': ['hearing', '청문회'],
        '지명': ['nominate', 'nominated', 'appointment', '지명'],
        '휴전': ['ceasefire', '휴전'],
        '철수': ['withdraw', 'withdrawal', '철수'],
        'ai': ['ai', 'artificial intelligence'],
		'예측시장': ['prediction market', 'prediction markets', '예측시장'],
        '클래리티법': ['clarity act', 'clarity', '클래리티법', '클래리티'],
        '감독': ['oversight', 'oversight authority', '감독'],
		'지니어스법': ['genius act', 'genius', '지니어스 법안', '지니어스법', '지니어스'],
'재무부': ['treasury', 'department of the treasury', '재무부'],
'의견수렴': ['public comment', 'seek comment', 'request for comment', '의견 수렴', '의견을 구함'],
'주정부규제': ['state level', 'state regulation', 'state oversight', '주 차원', '주정부 감독', '주정부 규제'],
'발행사': ['issuer', 'issuers', '발행사', '발행업체'],'내부자거래': ['insider trading', '내부자 거래'],
'규칙안': ['rules', 'rulemaking', '규칙안', '규칙'],
'기관진출': ['institutional entry', 'institutional access', '시장 진출', '기관 진출'],
		'시장구조법안': ['market structure bill', 'market structure', '시장 구조 법안', '시장구조법안'],
'스테이블코인수익': ['stablecoin yield', 'yield compromise', '스테이블코인 수익', '수익률 수정안'],
		        '스트래티지매수': ['strategy', 'strc', '스트래티지', '비트코인 매입', '비트코인 매수'],
        'cbdc예금토큰': ['cbdc', 'deposit token', '예금 토큰', '예금토큰'],
        '오픈ai이동': ['openai', 'emea', '정책 총괄', 'policy lead'],
        '암호화폐감독': ['crypto oversight', 'crypto supervision', '암호화폐 감독', '감독권'],
        '회로차단기': ['circuit breaker', '회로 차단기', '서킷 브레이커'],
        '가짜지갑사기': ['fake wallet', 'seed phrase', '가짜 지갑', '시드 구문'],
		        '부산은행토스': ['부산은행', 'bnk', '토스', 'toss'],
        '비트마인가': ['bitmine', '톰리', 'tom lee', 'ethereum'],
        'cftc전의장': ['cftc', 'christopher giancarlo', '크리스지안카를로'],
        '가수지갑사기': ['glove', 'g love', 'fake wallet', 'seed phrase', '가짜 지갑'],
        '크라켄유출거부': ['kraken', 'data leak', 'ransom', '유출', '몸값'],
		
    }

    for key, terms in topic_map.items():
        if any(contains_exact_term(text, t) for t in terms):
            parts.append(f'topic_{key}')

    # 기관 / 인물
    entity_map = {
        'hkma': ['hkma', 'hong kong monetary authority', '홍콩금융관리국'],
        'asic': ['asic'],
        'sec': ['sec'],
        'cftc': ['cftc'],
        'occ': ['occ'],
        '트럼프': ['donald trump', 'trump', '트럼프'],
        '케빈워시': ['kevin warsh', '케빈워시'],
        '마이클바': ['michael barr', '마이클바'],
        '잭도시': ['jack dorsey', '잭도시'],
        'hsbc': ['hsbc'],
        '스탠다드차타드': ['standard chartered', '스탠다드차타드'],
        'block': ['block'],
        '마이클셀릭': ['michael selig', '마이클셀릭', '마이클 셀릭'],
		'재무부': ['treasury', 'department of the treasury', '재무부'],
'지니어스그룹': ['genius group', '지니어스그룹'],
'empery': ['empery digital', 'empery'],'jpmorgan': ['jpmorgan', 'jp morgan', '제이피모건'],
'goldmansachs': ['goldman sachs', '골드만삭스'],
'paradigm': ['paradigm'],
'제이미다이먼': ['jamie dimon', '제이미다이먼', '제이미 다이먼'],
		        'strategy': ['strategy', 'strc', '스트래티지', 'michael saylor', '마이클세일러'],
        'bok': ['bank of korea', '한국은행', '신현송', 'hyun song shin'],
        'coinbase': ['coinbase', '코인베이스', 'tom duff gordon', '톰더프고든'],
        'openai': ['openai'],
        'ecb': ['ecb'],
        'esma': ['esma'],
        'bithumb': ['bithumb', '빗썸'],
        'kraken': ['kraken', '크라켄'],
		        'bnk': ['bnk', '부산은행'],
        'toss': ['toss', '토스'],
        'bitmine': ['bitmine', '비트마인', 'tom lee', '톰리'],
        'giancarlo': ['christopher giancarlo', '크리스지안카를로', 'cftc'],
        'glove': ['g love', 'glove', '싱어송라이터', '가수'],
    }

    for key, terms in entity_map.items():
        if any(contains_exact_term(text, t) for t in terms):
            parts.append(f'entity_{key}')

    # 액션
    action_map = {
        '통과': ['pass', 'passed', 'passes', 'approved', 'approval', '통과', '승인'],
        '지연': ['delay', 'delayed', 'missed target', 'behind schedule', '지연'],
        '출시': ['launch', 'launched', '출시'],
        '발언': ['said', 'says', 'statement', '밝힘', '전함', '발언'],
        '감축': ['job cuts', 'layoff', 'layoffs', '감축', '해고'],
		'강조': ['emphasized','warn', 'warning', 'emphasize', 'stressed', '강조', '경고'],
        '준비': ['prepared', 'ready', '준비'],
		        '이동': ['move', 'moved', 'joins', 'joined', 'appointed', '이동', '합류'],
        '매수': ['buy', 'bought', 'acquire', 'acquired', '매수', '매입'],
        '지지': ['support', 'supports', '지지'],
        '촉구': ['urge', 'urges', 'calls for', '촉구'],
    }

    for key, terms in action_map.items():
        if any(contains_exact_term(text, t) for t in terms):
            parts.append(f'action_{key}')

    # 너무 짧으면 중복키로 쓰지 않음
    parts = sorted(set(parts))
    if len(parts) < 3:
        return ""

    return " | ".join(parts)

def build_story_signature(story: dict) -> str:
    raw = f"{story.get('title', '')} {story.get('desc', '')}"
    text = normalize_for_duplicate(raw)

    tags = set()

    # 자산
    asset_map = {
        'btc': 'asset_btc',
        'bitcoin': 'asset_btc',
        'eth': 'asset_eth',
        'ethereum': 'asset_eth',
        'xrp': 'asset_xrp',
        'ripple': 'asset_xrp',
        'xrpl': 'asset_xrpl',
        'xrp ledger': 'asset_xrpl',
        'usdc': 'asset_usdc',
        'usdt': 'asset_usdt',
        'bch': 'asset_bch',
        'bitcoin cash': 'asset_bch',
        'shib': 'asset_shib',
        'shiba inu': 'asset_shib',

    }

    for key, value in asset_map.items():
        if key in text:
            tags.add(value)

    # 기관/회사
    org_map = {
        'occ': 'org_occ',
        'fed': 'org_fed',
        'federal reserve': 'org_fed',
        'treasury': 'org_treasury',
        'sec': 'org_sec',
        'cftc': 'org_cftc',
        'ripple': 'org_ripple',
        'bitget': 'org_bitget',
        'google': 'org_google',
        'openai': 'org_openai',
        'anthropic': 'org_anthropic',
        'block': 'org_block',
        'coinbase': 'org_coinbase',
		'treasury': 'org_treasury',
        'genius group': 'org_geniusgroup',
        'empery digital': 'org_empery',
        'fomc': 'org_fomc',
        'cme': 'org_cme',
        'qivalis': 'org_qivalis',
        'tempo': 'org_tempo',
        'moneygram': 'org_moneygram',
        'allunity': 'org_allunity',
        'kalqix': 'org_kalqix',
        'truth social': 'org_truthsocial',
        'tohoku bank': 'org_tohokubank',
        'sbi remit': 'org_sbiremit',
        'softbank': 'org_softbank',
        'whitebit': 'org_whitebit',
        'morgan stanley': 'org_morganstanley',
        'santiment': 'org_santiment',
        'santander': 'org_santander',
        'nuva': 'org_nuva',
		        'strategy': 'org_strategy',
        'strc': 'org_strategy',
        'michael saylor': 'org_strategy',
        '스트래티지': 'org_strategy',
        '마이클세일러': 'org_strategy',

        'bank of korea': 'org_bok',
        '한국은행': 'org_bok',
        '신현송': 'person_hyunsongshin',
        'hyun song shin': 'person_hyunsongshin',

        'coinbase': 'org_coinbase',
        'openai': 'org_openai',
        'tom duff gordon': 'person_tomduffgordon',
        '톰더프고든': 'person_tomduffgordon',

        'ecb': 'org_ecb',
        'esma': 'org_esma',

        'bithumb': 'org_bithumb',
        '빗썸': 'org_bithumb',

        'kraken': 'org_kraken',
        '애플': 'org_apple',
        'apple': 'org_apple',
		'bnk': 'org_bnk',
        '부산은행': 'org_bnk',
        'toss': 'org_toss',
        '토스': 'org_toss',
        'bitmine': 'org_bitmine',
        '비트마인': 'org_bitmine',
        'christopher giancarlo': 'person_giancarlo',
        '크리스지안카를로': 'person_giancarlo',
        'g love': 'person_glove',
        'glove': 'person_glove',
    }

    for key, value in org_map.items():
        if key in text:
            tags.add(value)

    # 액션
    action_map = {
        'approval': 'act_approval',
        'approve': 'act_approval',
        'bank charter': 'act_bank_charter',
        'custody': 'act_custody',
        'integration': 'act_integration',
        'integrated': 'act_integration',
        'payment': 'act_payment',
        'payments': 'act_payment',
        'staking': 'act_staking',
        'unlock': 'act_unlock',
        'unlocked': 'act_unlock',
        'surveillance': 'act_surveillance',
        '감시': 'act_surveillance',
        'regulation': 'act_regulation',
        'bill': 'act_bill',
        'law': 'act_law',
        'risk': 'act_risk',
        'adoption': 'act_adoption',
        'institutional': 'act_institutional',
 		'comment': 'act_comment',
        'issuer': 'act_issuer',
        'repay': 'act_repay',
        'sale': 'act_sale',
        'sold': 'act_sale',
        '매각': 'act_sale',
        '상환': 'act_repay',
        '의견 수렴': 'act_comment',
		        'move': 'act_move',
        'joins': 'act_move',
        'joined': 'act_move',
        'appointed': 'act_move',
        'hire': 'act_move',
        'hired': 'act_move',
        '이동': 'act_move',
        '합류': 'act_move',

        'supports': 'act_support',
        'support': 'act_support',
        '지지': 'act_support',

        'calls for': 'act_policy',
        'urges': 'act_policy',
        '촉구': 'act_policy',

        'bought': 'act_buy',
        'buy': 'act_buy',
        '매입': 'act_buy',
        '매수': 'act_buy',
		'stolen': 'act_theft',
        'theft': 'act_theft',
        '도난': 'act_theft',
        'leak': 'act_leak',
        'leaked': 'act_leak',
        '유출': 'act_leak',
        'refuse': 'act_refuse',
        'refused': 'act_refuse',
        '거부': 'act_refuse',
    }

    for key, value in action_map.items():
        if key in text:
            tags.add(value)



    return ' | '.join(sorted(tags))


def is_semantically_duplicate(story: dict, seen_signatures: list[str], seen_titles: list[str]) -> bool:
    title = normalize_for_duplicate(story.get('title', ''))
    signature = build_story_signature(story)

    # 제목 유사도는 조금 완화
    for old_title in seen_titles:
        ratio = SequenceMatcher(None, title, old_title).ratio()
        if ratio >= 0.88:
            log(f"[제목유사도 중복] {title} <> {old_title} / {ratio:.2f}")
            return True

    # 시그니처가 너무 짧으면 중복판단 안 함
    if len(signature.split('|')) < 3:
        return False

    # 액션(act_)이 같은 경우에만 강하게 중복 판정
    current_actions = {x for x in signature.split('|') if x.strip().startswith('act_')}

    for old_sig in seen_signatures:
        old_actions = {x for x in old_sig.split('|') if x.strip().startswith('act_')}

        if not current_actions or not old_actions:
            continue

        if current_actions and old_actions and current_actions.isdisjoint(old_actions):
            continue

        ratio = SequenceMatcher(None, signature, old_sig).ratio()
        if ratio >= 0.92:
            log(f"[시그니처 유사도 중복] {signature} <> {old_sig} / {ratio:.2f}")
            return True

    return False


def format_summary_for_telegram(text: str, max_sentences: int = 3, max_chars: int = 120) -> str:
    text = (text or "").strip()
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{2,}', '\n', text).strip()

    # 문장 단위 분리
    sentences = re.split(r'(?<=[.!?])\s+|(?<=음)\s+|(?<=임)\s+|(?<=됨)\s+|(?<=함)\s+|(?<=밝힘)\s+|(?<=전함)\s+', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    picked = []
    total = 0

    for s in sentences:
        if len(picked) >= max_sentences:
            break
        if picked and total + len(s) > max_chars:
            break
        picked.append(s)
        total += len(s)

    if not picked and text:
        picked = [text[:max_chars].rstrip()]

    # 문장 끝마다 한 줄 띄우기
    return '\n\n'.join(picked).strip()

def finalize_summary_ending(text: str) -> str:
    text = re.sub(r'좋은\s*덩어리$', '', text)

    text = re.sub(r'([가-힣]+)음고 말함$', r'\1음', text)
    text = re.sub(r'([가-힣]+)고 말함$', r'\1', text)

    text = re.sub(r'문제가 아니\.$', '문제가 아님', text)
    text = re.sub(r'아니\.$', '아님', text)
    text = re.sub(r'될 것\.$', '될 것임', text)
    text = re.sub(r'계획이\.$', '계획임', text)
    text = re.sub(r'보인다\.$', '보임', text)
    text = re.sub(r'전망이다\.$', '전망임', text)

    text = re.sub(r'매도가 있었음.*$', '매도가 있었음', text)
    text = re.sub(r'커졌음.*$', '커졌음', text)

    text = re.sub(r'했음고', '했고', text)
    text = re.sub(r'했음는', '했다는', text)
    text = text.replace('있음고', '있다고')
    text = text.replace('변화할 것임.', '변화할 것임')
    text = re.sub(r'#([A-Za-z0-9가-힣]+)\s+\n', r'#\1\n', text)

    text = re.sub(r'\s+', ' ', text).strip()
    return text
	


def _normalize_footer_tags(tags: list[str]) -> list[str]:
    if not tags:
        return []

    mapping = {
        '#Japan': '#일본',
        '#Bhutan': '#부탄',
        '#Germany': '#독일',
        '#USA': '#US',
        '#UnitedStates': '#US',
        '#America': '#US',
        '#Ripple': '#XRP',
        '#RL#미국D': '#RLUSD',
        '#F O M C': '#FOMC',
        '#HesterPeirce': '#헤스터피어스',
        '#CME': '#시카고상품거래소(CME)',
        '#Qivalis': '#키발리스',
        '#RaoulPal': '#라울팔',
        '#Nuva': '#누바',
        '#Tempo': '#템포',
        '#MoneyGram': '#머니그램',
        '#Muro': '#무로',
        '#Santander': '#산탄데르',
        '#Michael Saylor': '#MichaelSaylor',
        '#Wall Street': '#WallStreet',
        '#Black Rock': '#BlackRock',
    }
    out=[]
    seen=set()
    for tag in tags:
        tag = (tag or '').strip()
        if not tag:
            continue
        if not tag.startswith('#'):
            tag = '#' + tag
        tag = mapping.get(tag, tag)
        tag = re.sub(r'\s+', '', tag)
        if tag == '#리플':
            tag = '#XRP'
        if tag and tag not in seen:
            out.append(tag)
            seen.add(tag)
    return out


def restore_telegram_linebreaks(text: str) -> str:
    text = (text or '').replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'[ \t]+', ' ', text).strip()
    if '\n\n' in text:
        return text
    if len(text) > 70:
        m = re.search(r'(임|함|됨|밝힘|전함|설명함|추진 중|검토 중)', text)
        if m:
            cut = m.end()
            left = text[:cut].strip()
            right = text[cut:].strip()
            if left and right:
                text = left + '\n\n' + right
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    return text


INLINE_KO_ENTITY_TAGS = [
    ('그리스', [r'\bgreece\b', r'그리스']),
    ('국가정보국', [r'\bodni\b', r'국가정보국', r'national intelligence']),
    ('ODNI', [r'\bodni\b']),
    ('월가', [r'wall\s*street', r'월가']),
    ('사이버펑크', [r'cypherpunk', r'사이버펑크']),
    ('마이클셰일러', [r'michael\s*saylor', r'마이클\s*세일러', r'마이클셰일러']),
    ('블랙록', [r'blackrock', r'블랙록']),
    ('연준', [r'\bfed\b', r'federal reserve', r'연준']),
    ('FOMC', [r'\bfomc\b']),
    ('트럼프', [r'trump', r'트럼프']),
    ('미국', [r'\bu\.?s\.?\b', r'\busa\b', r'\bunited states\b', r'미국']),
]

FOOTER_EN_TAGS_MAP = {
    '그리스': '#Greece',
    '국가정보국': '#ODNI',
    'ODNI': '#ODNI',
    '월가': '#WallStreet',
    '사이버펑크': '#Cypherpunk',
    '마이클셰일러': '#MichaelSaylor',
    '블랙록': '#BlackRock',
    '연준': '#FOMC',
    'FOMC': '#FOMC',
    '트럼프': '#Trump',
    '미국': '#US',
}

def ensure_inline_entity_tags(text: str, raw_text: str) -> str:
    if not text:
        return ''
    base = f"{text}\n{raw_text or ''}".lower()
    found = []
    for label, patterns in INLINE_KO_ENTITY_TAGS:
        for pat in patterns:
            if re.search(pat, base, re.I):
                found.append(f'#{label}')
                break
    if not found:
        return text
    lines = [ln.strip() for ln in text.splitlines()]
    if not lines:
        return text
    first = lines[0]
    existing = set(re.findall(r'#[A-Za-z0-9가-힣_]+', text))
    add_tags = [t for t in found if t not in existing]
    if add_tags:
        first = ' '.join(add_tags) + ' ' + first
    lines[0] = re.sub(r'\s+', ' ', first).strip()
    return '\n'.join(lines).strip()

def fix_korean_hashtag_particles(text: str) -> str:
    if not text:
        return ''
    particle_rules = [
        '에서의', '에게', '으로', '와의', '과의', '에는', '에도', '에서',
        '은', '는', '이', '가', '을', '를', '와', '과', '도', '만', '에', '로', '의'
    ]
    for p in particle_rules:
        text = re.sub(rf'(#[A-Za-z0-9가-힣_]+){p}(?=[^A-Za-z0-9가-힣_]|$)', rf'\1 {p}', text)
    text = re.sub(r'\s+([,])', r'\1', text)
    return text.strip()

def fix_split_person_tags(text: str) -> str:
    if not text:
        return ''
    name_join_rules = [
        (r'마이클\s+#셰일러', '#마이클셰일러'),
        (r'마이클\s+셰일러', '#마이클셰일러'),
        (r'찰스\s+#호스킨슨', '#찰스호스킨슨'),
        (r'찰스\s+호스킨슨', '#찰스호스킨슨'),
        (r'데이비드\s+#슈워츠', '#데이비드슈워츠'),
        (r'데이비드\s+슈워츠', '#데이비드슈워츠'),
        (r'브래드\s+#갈링하우스', '#브래드갈링하우스'),
        (r'브래드\s+갈링하우스', '#브래드갈링하우스'),
    ]
    for pat, repl in name_join_rules:
        text = re.sub(pat, repl, text)
    return text.strip()

def collect_footer_entity_tags(summary: str, raw_text: str) -> list[str]:
    base = f"{summary}\n{raw_text or ''}".lower()
    tags = []
    for ko, en in FOOTER_EN_TAGS_MAP.items():
        if re.search(rf'#{re.escape(ko)}(?=[^A-Za-z0-9가-힣_]|$)', summary):
            tags.append(en)
            continue
        for label, patterns in INLINE_KO_ENTITY_TAGS:
            if label != ko:
                continue
            for pat in patterns:
                if re.search(pat, base, re.I):
                    tags.append(en)
                    break
    seen = set()
    out = []
    for t in tags:
        if t not in seen:
            out.append(t)
            seen.add(t)
    return out


def build_message(story: dict) -> str:
    title = story.get('title', '')
    desc = story.get('desc', '')
    article_text = get_best_source_text(story)

    summary_ko = rewrite_summary_with_gemini(
        title=title,
        article_text=article_text,
        fallback_text=desc
    )

    if is_refusal_or_skip_text(summary_ko):
        log(f"[차단문구/요약거부 스킵] {title}")
        return ""

    if not summary_ko:
        log(f"[요약실패 스킵] {title}")
        return ""

    # 기사 원문/제목 + 요약문 둘 다 기준으로 엔티티 추출
    story_entities = extract_entities(story, max_tags=12)
    summary_entities = extract_entities_from_summary(summary_ko, max_tags=12)

    merged_entities = []
    seen_entities = set()
    for e in story_entities + summary_entities:
        key = e.lower()
        if key not in seen_entities:
            merged_entities.append(e)
            seen_entities.add(key)

    entities = [
        e for e in merged_entities
        if e in INLINE_TAG_WHITELIST or entity_korean_name(e) in INLINE_TAG_WHITELIST
    ]

    summary_ko, dynamic_tags = inject_entity_hashtags(summary_ko, entities)
    summary_ko = fix_broken_inline_hashtags(summary_ko)
    summary_ko = remove_duplicate_inline_hashtags(summary_ko)
    summary_ko = finalize_summary_ending(summary_ko)

    raw_text = f"{title}\n{desc}"
    summary = summary_ko if summary_ko else story.get('title', '')
    summary = format_summary_for_telegram(summary, max_sentences=3, max_chars=115)
    summary = ensure_inline_entity_tags(summary, raw_text)
    summary = fix_split_person_tags(summary)
    summary = fix_korean_hashtag_particles(summary)
    summary = restore_telegram_linebreaks(summary)
    summary = summary.replace('자동뉴스', '').strip()
    summary = summary.replace('다음 기사는', '').strip()
    summary = summary.replace('뉴스레터', '').strip()
    summary = summary.replace('가상자산', '암호화폐')
    summary = summary.replace('리플 얼라이언스', 'XRP 얼라이언스')
    summary = summary.replace('리플 고래', 'XRP 고래')
    summary = summary.replace('리플 선물', 'XRP 선물')
    summary = summary.replace('Santiment', '샌티먼트')
    summary = summary.replace('Hester Peirce', '헤스터피어스')
    summary = summary.replace('FOMC 회의록', '#FOMC 회의록')
    summary = summary.replace('연준은', '#연준 은')
    summary = summary.replace('연준 의장', '#연준 의장')
    summary = summary.replace('CME ', '시카고상품거래소(CME) ')
    summary = summary.replace('Qivalis', '키발리스')
    summary = summary.replace('Raoul Pal', '라울팔')
    summary = summary.replace('NUVA', '누바')
    summary = summary.replace('Tempo', '템포')
    summary = summary.replace('MoneyGram', '머니그램')
    summary = summary.replace('MiCA', '미카')
    summary = summary.replace('Truth Social', '트루스소셜')
    summary = summary.replace('Tohoku Bank', '도호쿠은행')
    summary = summary.replace('SoftBank', '소프트뱅크')
    summary = summary.replace('Twenty One Capital', '트웬티원캐피털')
    summary = summary.replace('WhiteBIT', '화이트비트')
    summary = summary.replace('Timothy Massad', '티머시매사드')

    summary = fix_split_person_tags(summary)
    summary = fix_korean_hashtag_particles(summary)

    dynamic_tags = filter_final_tags(dynamic_tags)
    footer_tags = dynamic_tags + [f'#{t}' for t in FINAL_HASHTAGS]
    extra_footer_tags = collect_footer_entity_tags(summary, raw_text)
    for tag in extra_footer_tags:
        if tag not in footer_tags:
            footer_tags.append(tag)
    footer_tags = _normalize_footer_tags(footer_tags)

    inline_tags = set(re.findall(r'#[A-Za-z0-9가-힣]+', summary))
    footer_tags = [t for t in footer_tags if t not in inline_tags]

    seen = set()
    dedup = []
    for t in footer_tags:
        if t not in seen:
            dedup.append(t)
            seen.add(t)

    parts = [
        html.escape(summary),
        '🌐 <a href="http://t.me/Doorinews">공식 글로벌 실시간 도리뉴스</a>',
        f'<a href="{html.escape(story.get("url", ""))}">출처</a>',
        ' '.join(html.escape(t) for t in dedup)
    ]

    return '\n\n'.join(parts)

def send_telegram_message(token: str, channel: str, message: str) -> bool:
    if not token or not channel:
        log("Telegram token or channel not set")
        return False
    payload = json.dumps({
        'chat_id': channel,
        'text': message[:4000],
        'parse_mode': 'HTML',
        'disable_web_page_preview': True
    }).encode('utf-8')
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    try:
        req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=20) as resp:
            log(resp.read().decode('utf-8', errors='ignore'))
        return True
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='ignore')
        log(f"Error sending message: HTTP {e.code} {e.reason} | {body}")
        return False
    except Exception as e:
        log(f"Error sending message: {e}")
        return False

def send_telegram_photo(token: str, channel: str, image_url: str, caption: str) -> bool:
    if not token or not channel:
        log("Telegram token or channel not set")
        return False
    if not image_url:
        log("[이미지없음 게시차단] 사진 URL을 확보하지 못해 기사를 게시하지 않음")
        return False
    while len(caption.encode('utf-8')) > 1000:
        caption = caption[:-1]
    payload = json.dumps({
        'chat_id': channel,
        'photo': image_url,
        'caption': caption,
        'parse_mode': 'HTML'
    }).encode('utf-8')
    url = f'https://api.telegram.org/bot{token}/sendPhoto'
    try:
        req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=25) as resp:
            log(resp.read().decode('utf-8', errors='ignore'))
        return True
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='ignore')
        log(f"[이미지전송실패 게시차단] HTTP {e.code} {e.reason} | {body}")
        return False
    except Exception as e:
        log(f"[이미지전송실패 게시차단] {e}")
        return False



def prune_posted_older_than(posted: dict, days: int = 30) -> dict:
    if not isinstance(posted, dict):
        return {}

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    pruned = {}

    for k, v in posted.items():
        try:
            ts = v.get("ts", "")
            if not ts:
                continue

            dt = datetime.fromisoformat(ts)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

            if dt >= cutoff:
                pruned[k] = v
        except Exception:
            continue

    return pruned

def main():
    log("Bot starting...")
    log("RUNNING_BUILD=0620_general_duplicate_engine")
    state = load_state(STATE_FILE)
    posted = state.get('posted', {})

    before_cnt = len(posted)
    posted = prune_posted_older_than(posted, days=30)
    after_cnt = len(posted)
    state['posted'] = posted
    save_state(STATE_FILE, state)
    log(f"[state 정리] 30일 초과 삭제: {before_cnt - after_cnt}개 / 유지: {after_cnt}개")

    collected = []

    for name, feed_url in FEEDS:
        stories = fetch_rss(feed_url, max_items=MAX_ITEMS_PER_FEED)
        log(f"{name}: {len(stories)}개 수집")
        collected.extend(stories)

    filtered = [s for s in collected if matches_keywords(s, PORTFOLIO_COINS, ECON_KEYWORDS, KOREAN_KEYWORDS)]
    log(f"전체 수집 {len(collected)}개 / 필터 통과 {len(filtered)}개")

    new_stories = []
    seen_titles = [
        normalize_for_duplicate(item.get('title', ''))
        for item in posted.values()
        if item.get('title')
    ]
    seen_signatures = [
        item.get('signature', '')
        for item in posted.values()
        if item.get('signature')
    ]
    seen_urls = {
        item.get('url', '').strip()
        for item in posted.values()
        if item.get('url')
    }
    seen_topic_keys = {
        item.get('signature', '')
        for item in posted.values()
        if item.get('signature')
    }

    seen_canonical_keys = {
        item.get('canonical_key', '')
        for item in posted.values()
        if item.get('canonical_key')
    }

    for s in filtered:
        title = s.get('title', '')
        norm_title = normalize_for_duplicate(title)
        signature = build_story_signature(s)
        canonical_key = build_canonical_topic_key(s)
        url = s.get('url', '').strip()

        current_actions = {x for x in signature.split('|') if x.strip().startswith('act_')}

        if (
            signature
            and len(signature.split('|')) >= 3
            and signature in seen_topic_keys
        ):
            log(f"[토픽중복 제외] {title}")
            log(f"  └ 시그니처: {signature}")
            continue

        if is_canonical_duplicate(canonical_key, seen_canonical_keys):
            log(f"[정규토픽중복 제외] {title}")
            log(f"  └ canonical_key: {canonical_key}")
            continue
  
        if url and url in seen_urls:
            log(f"[URL중복 제외] {title}")
            continue

        if is_duplicate(title, posted, url):
            log(f"[제목/URL중복 제외] {title}")
            continue

        if is_semantically_duplicate(s, seen_signatures, seen_titles):
            log(f"[의미중복 제외] {title}")
            log(f"  └ 정규화제목: {norm_title}")
            log(f"  └ 시그니처: {signature}")
            continue

        log(f"[통과] {title}")
        log(f"  └ 정규화제목: {norm_title}")
        log(f"  └ 시그니처: {signature}")

        new_stories.append(s)
        seen_titles.append(norm_title)
        seen_signatures.append(signature)

        if signature and len(signature.split('|')) >= 3:
            seen_topic_keys.add(signature)

        if canonical_key:
            seen_canonical_keys.add(canonical_key)

        if url:
            seen_urls.add(url)

    log(f"중복 제거 후 {len(new_stories)}개")
    state['posted'] = posted
    save_state(STATE_FILE, state)

    if INITIAL_RUN:
        log("INITIAL_RUN=true 상태라 텔레그램 발송 없이 종료")
        return

    if not POST_ENABLED:
        log("POST_ENABLED=false 상태라 텔레그램 발송 없이 종료")
        log(f"발송 차단된 후보: {len(new_stories)}개")

        if DRY_RUN_RECORD:
            log("DRY_RUN_RECORD=true 상태라 발송 없이 news_state.json에 기록만 진행")
            for story in new_stories:
                signature = build_story_signature(story)
                canonical_key = build_canonical_topic_key(story)
                update_posted(
                    story.get('title', ''),
                    posted,
                    story.get('url', ''),
                    signature,
                    canonical_key
                )
            state['posted'] = posted
            save_state(STATE_FILE, state)
            log(f"발송 없이 기록 완료: {len(new_stories)}개")
        else:
            log("DRY_RUN_RECORD=false 상태라 기록도 하지 않음")

        return

    for story in new_stories:
        story['image_url'] = story.get('image_url', '') or fetch_article_meta(story.get('url', ''))[1]
        msg = build_message(story)

        if not msg.strip():
            log(f"[빈메시지 스킵] {story.get('title', '')}")
            continue

        log(f"[전송준비] title={story.get('title','')[:80]}")
        log(f"[전송준비] image_url={story.get('image_url','')}")
        ok = send_telegram_photo(
            TELEGRAM_BOT_TOKEN,
            TELEGRAM_CHANNEL_ID,
            story.get('image_url', ''),
            msg
        )

        if ok:
            signature = build_story_signature(story)
            canonical_key = build_canonical_topic_key(story)
            update_posted(
                story['title'],
                posted,
                story.get('url', ''),
                signature,
                canonical_key
            )
            state['posted'] = posted
            save_state(STATE_FILE, state)
            log(f"Posted: {story['title']}")
        else:
            log(f"Failed: {story['title']}")

        time.sleep(0.3)



# ---------------------------------------------------------------------------
# PATCH: 2026-05-20 duplicate / readability / tag refinement
# ---------------------------------------------------------------------------

_OLD_matches_keywords = matches_keywords
_OLD_build_story_signature = build_story_signature
_OLD_build_canonical_topic_key = build_canonical_topic_key
_OLD_is_canonical_duplicate = is_canonical_duplicate
_OLD_is_semantically_duplicate = is_semantically_duplicate
_OLD_format_summary_for_telegram = format_summary_for_telegram

INLINE_TAG_WHITELIST.update({
    '엘리자베스워런', 'OCC', '신탁은행', '엑스알피얼라이언스', '디센트',
    '아이렌', '엔비디아', '트럼프', '연준', '마스터계정',
    '한화투자증권', '두나무', '금융', '위메이드', 'NICE정보통신',
    'RWA', '토큰화', '스테이블코인', '독일', '유니온인베스트먼트',
    'CNBC', '케빈워시', 'BC카드', '결제', '인프라', '아베', 'WETH', 'rsETH',
    '일본', '부탄', '시장구조법안'
})

MANUAL_TRANSLATIONS.update({
    'Elizabeth Warren': '엘리자베스워런',
    'Warren': '엘리자베스워런',
    'OCC': 'OCC',
    'trust bank': '신탁은행',
    "D'CENT": '디센트',
    'D’CENT': '디센트',
    'DCENT': '디센트',
    'XRP Alliance': '엑스알피얼라이언스',
    'IREN': '아이렌',
    'Iris Energy': '아이렌',
    'NVIDIA': '엔비디아',
    'Federal Reserve': '연준',
    'Fed': '연준',
    'master account': '마스터계정',
    'Hanwha Investment Securities': '한화투자증권',
    'Hanwha Investment': '한화투자증권',
    'Dunamu': '두나무',
    'Wemade': '위메이드',
    'NICE Information & Telecommunication': 'NICE정보통신',
    'NICE Information&Telecommunication': 'NICE정보통신',
    'Union Investment': '유니온인베스트먼트',
    'Kevin Warsh': '케빈워시',
    'BC Card': 'BC카드',
    'Aave': '아베',
    'CLARITY Act': '시장구조법안',
    'CLARITY': '시장구조법안',
})

_EXTRA_NEGATIVE_PATTERNS = [
    r'\bcrypto longs?\b', r'\blongs? lose\b', r'\bshorts?\b',
    r'\bliquidation(?:s)?\b', r'\bliquidated\b',
    r'롱\s*베팅', r'숏\s*베팅', r'선물\s*시장', r'청산', r'대규모\s*청산',
    r'시장\s*심리', r'심리\s*악화', r'심리\s*위축',
    r'하락함', r'상승함', r'급락', r'급등', r'하락세', r'약세', r'반등',
    r'선\s*유지', r'77,?000\s*달러\s*선', r'가격이\s*[^\n]{0,12}(유지|깨짐|뚫|돌파)', r'현물\s*etf\s*유출',
]

_EVENT_RULES = {
    'ent_warren': [r'elizabeth warren', r'\bwarren\b', r'엘리자베스\s*워런', r'엘리자베스워런'],
    'ent_occ': [r'\bocc\b', r'통화감독청'],
    'obj_trustbank': [r'trust bank', r'신탁\s*은행'],
    'act_probe': [r'investigat', r'조사', r'문제\s*삼', r'문제제기', r'착수'],
    'ent_dcent': [r"d[’']?cent", r'디센트'],
    'ent_xrp_alliance': [r'xrp alliance', r'엑스알피얼라이언스'],
    'obj_rewards': [r'earnxrp', r'mxrpy', r'수익금고', r'리워드', r'금고'],
    'act_connect': [r'connect', r'연결', r'제공'],
    'ent_iren': [r'\biren\b', r'iris energy', r'아이렌'],
    'ent_nvidia': [r'nvidia', r'엔비디아'],
    'obj_ai_cloud': [r'ai cloud', r'인프라 클라우드', r'hpc', r'고성능 컴퓨팅'],
    'act_convert': [r'전환', r'본격화', r'가속화', r'확보'],
    'ent_trump': [r'\btrump\b', r'트럼프'],
    'ent_fed': [r'federal reserve', r'\bfed\b', r'연준'],
    'obj_master_account': [r'master account', r'마스터\s*계정'],
    'act_review': [r'검토', r'명령', r'접근\s*권한'],
    'ent_hanwha': [r'한화투자증권', r'hanwha investment'],
    'ent_dunamu': [r'\bdunamu\b', r'두나무'],
    'act_invest': [r'투자', r'지분', r'매수'],
    'amt_6000eok': [r'6000억', r'9\.84%'],
    'ent_wemade': [r'위메이드', r'\bwemade\b'],
    'ent_nice': [r'nice정보통신', r'nice information'],
    'obj_mou': [r'\bmou\b', r'협약', r'체결'],
    'obj_payment': [r'결제\s*인프라', r'웹3\s*결제', r'결제'],
    'ent_union': [r'union investment', r'유니온인베스트먼트'],
    'geo_germany': [r'germany', r'독일'],
    'obj_stablecoin_safety': [r'스테이블코인', r'usdc', r'usdt'],
    'act_warn': [r'안전하지\s*않', r'보지\s*않', r'경고', r'설명'],
    'ent_cnbc': [r'\bcnbc\b'],
    'obj_innovation50': [r'혁신\s*기업\s*50', r'innovation 50'],
    'ent_kevinwarsh': [r'kevin warsh', r'케빈\s*워시', r'케빈워시'],
    'obj_asset_sale': [r'자산을?\s*매각', r'매각함', r'매각'],
    'ent_bccard': [r'bc카드', r'\bbc card\b'],
    'obj_patent': [r'특허', r'인프라\s*확장'],
    'ent_aave': [r'\baave\b', r'아베'],
    'obj_weth': [r'\bweth\b', r'rseth', r'담보인정비율', r'복구'],
    'geo_japan': [r'japan', r'일본'],
    'geo_bhutan': [r'bhutan', r'부탄'],
    'bill_clarity': [r'clarity act', r'시장구조법안', r'클래리티'],
    'ent_qivalis': [r'qivalis', r'키발리스'],
    'ent_raoulpal': [r'raoul pal', r'라울팔', r'라울\s*팔'],
    'ent_nuva': [r'\bnuva\b', r'누바'],
    'ent_tempo': [r'\btempo\b', r'템포'],
    'ent_moneygram': [r'moneygram', r'머니그램'],
    'ent_muro': [r'\bmuro\b', r'무로'],
    'ent_santander': [r'santander', r'산탄데르'],
    'ent_fomc': [r'\bfomc\b', r'FOMC'],
    'ent_hester': [r'hester peirce', r'헤스터\s*피어스', r'헤스터피어스'],
    'ent_cme': [r'\bcme\b', r'cme group', r'chicago mercantile exchange', r'시카고상품거래소'],
    'obj_line_hold': [r'77,?000', r'선\s*유지', r'선을?\s*걸고?\s*유지', r'깨짐', r'뚫', r'돌파', r'지지선', r'저항선'],
}


def _story_text(story: dict) -> str:
    return f"{story.get('title','')} {story.get('desc','')}"

def _extract_event_markers(text: str) -> list[str]:
    low = normalize_for_duplicate(text)
    out = []
    for key, patterns in _EVENT_RULES.items():
        for pat in patterns:
            if re.search(pat, low, re.I):
                out.append(key)
                break
    if re.search(r'72만|720000|720,?000', low):
        out.append('amt_72man')
    if re.search(r'34억\s*달러|3\.4\s*billion', low):
        out.append('amt_34eok_dollar')
    if re.search(r'1억\s*9300만\s*달러|193 million', low):
        out.append('amt_193m')
    if re.search(r'630억\s*달러|63 billion', low):
        out.append('amt_63b')
    if re.search(r'4,?500억\s*개|450 billion', low):
        out.append('amt_450b_units')
    if re.search(r'25개\s*은행|37개\s*은행', low):
        out.append('obj_bank_expansion')
    return sorted(set(out))

def _normalize_signature_parts(parts):
    return sorted(set([p.strip() for p in parts if p and p.strip()]))

def build_story_signature(story: dict) -> str:
    base = _OLD_build_story_signature(story)
    parts = [p.strip() for p in base.split('|') if p.strip()]
    parts.extend(_extract_event_markers(_story_text(story)))
    return ' | '.join(_normalize_signature_parts(parts))

def build_canonical_topic_key(story: dict) -> str:
    base = _OLD_build_canonical_topic_key(story)
    parts = [p.strip() for p in base.split('|') if p.strip()]
    parts.extend(_extract_event_markers(_story_text(story)))
    return ' | '.join(_normalize_signature_parts(parts))

def _core_event_tokens(key: str) -> set:
    toks = {x.strip() for x in (key or '').split('|') if x.strip()}
    return {t for t in toks if not t.startswith('asset_') and not t.startswith('geo_')}

def is_canonical_duplicate(canonical_key: str, seen_keys: set[str]) -> bool:
    if not canonical_key:
        return False
    cur_all = {x.strip() for x in canonical_key.split('|') if x.strip()}
    cur_core = _core_event_tokens(canonical_key)

    for old_key in seen_keys:
        old_all = {x.strip() for x in old_key.split('|') if x.strip()}
        old_core = _core_event_tokens(old_key)
        shared_core = cur_core & old_core
        shared_all = cur_all & old_all

        if len(shared_core) >= 2:
            log(f"[정규토픽중복 제외] shared_core={shared_core}")
            return True
        if len(shared_all) >= 4 and len(shared_core) >= 1:
            log(f"[정규토픽유사 제외] shared_all={shared_all}")
            return True
    return False

def is_semantically_duplicate(story: dict, seen_signatures: list[str], seen_titles: list[str]) -> bool:
    title = normalize_for_duplicate(story.get('title', ''))
    signature = build_story_signature(story)
    cur_all = {x.strip() for x in signature.split('|') if x.strip()}
    cur_core = _core_event_tokens(signature)

    for old_title in seen_titles:
        ratio = SequenceMatcher(None, title, old_title).ratio()
        if ratio >= 0.92:
            log(f"[제목유사도 중복] {title} <> {old_title} / {ratio:.2f}")
            return True

    if len(cur_all) < 3:
        return False

    for old_sig in seen_signatures:
        old_all = {x.strip() for x in old_sig.split('|') if x.strip()}
        old_core = _core_event_tokens(old_sig)
        shared_core = cur_core & old_core
        shared_all = cur_all & old_all

        if not shared_core:
            continue
        if len(shared_core) >= 2:
            log(f"[의미중복 제외] shared_core={shared_core}")
            return True
        if len(shared_core) >= 1 and len(shared_all) >= 4:
            log(f"[시그니처 교집합 중복] {signature} <> {old_sig}")
            return True
        ratio = SequenceMatcher(None, signature, old_sig).ratio()
        if len(shared_core) >= 1 and ratio >= 0.93:
            log(f"[시그니처 유사도 중복] {signature} <> {old_sig} / {ratio:.2f}")
            return True

    return False

def matches_keywords(story: dict, coins: list[str], econ_keywords: list[str], korean_keywords: list[str]) -> bool:
    raw_text = _story_text(story)
    raw_lower = raw_text.lower()

    if any(re.search(p, raw_lower, re.I) for p in _EXTRA_NEGATIVE_PATTERNS):
        print(f"[시황심리/롱숏 제외] {story.get('title', '')}")
        return False

    return _OLD_matches_keywords(story, coins, econ_keywords, korean_keywords)

def _clean_summary_for_style(text: str) -> str:
    text = text or ""
    text = text.replace('가상자산', '암호화폐')
    text = text.replace('있음고', '있다고')
    text = text.replace('RL#미국D', '#RLUSD').replace('#R L U S D', '#RLUSD')
    text = text.replace('리플 얼라이언스', 'XRP 얼라이언스')
    text = text.replace('리플 고래', 'XRP 고래')
    text = text.replace('리플 선물', 'XRP 선물')
    text = re.sub(r'시장 심리[^.\n]*', '', text)
    text = re.sub(r'가격을 끌어올리지 못함', '', text)
    text = re.sub(r'(?<!#)리플(?=\s*고래|\s*선물|\s*현물|\s*토큰|\s*네트워크|\s*얼라이언스)', 'XRP', text)
    text = re.sub(r'(?<!#)XRP(?=\s*(고래|선물|현물|보유량|리워드|토큰))', '#XRP', text, count=1)
    text = re.sub(r'(?<!#)FOMC(?=\s)', '#FOMC', text, count=1)
    text = re.sub(r'(?<!#)헤스터피어스(?=\s)', '#헤스터피어스', text, count=1)
    text = re.sub(r'(?<!#)시카고상품거래소\(CME\)(?=\s)', '#시카고상품거래소(CME)', text, count=1)
    text = re.sub(r'(?<!#)키발리스(?=\s|[가-힣])', '#키발리스', text, count=1)
    text = re.sub(r'(?<!#)라울팔(?=\s)', '#라울팔', text, count=1)
    text = re.sub(r'(?<!#)누바(?=\s|,|\()', '#누바', text, count=1)
    text = re.sub(r'(?<!#)템포(?=\s|,|\()', '#템포', text, count=1)
    text = re.sub(r'(?<!#)무로(?=\s|,)', '#무로', text, count=1)
    text = re.sub(r'(?<!#)산탄데르(?=\s|,)', '#산탄데르', text, count=1)
    text = re.sub(r'(?<!#)RLUSD(?=\s|,|\))', '#RLUSD', text, count=1)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def format_summary_for_telegram(text: str, max_sentences: int = 3, max_chars: int = 110) -> str:
    text = _clean_summary_for_style(text)
    text = (text or "").replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'\n{2,}', '\n', text).strip()
    text = re.sub(r'[ \t]+', ' ', text)

    chunks = [c.strip() for c in text.split('\n') if c.strip()]
    if len(chunks) >= 2:
        picked = []
        total = 0
        for c in chunks:
            if len(picked) >= max_sentences:
                break
            if picked and total + len(c) > max_chars:
                break
            picked.append(c)
            total += len(c)
        if picked:
            return '\n\n'.join(picked).strip()

    return _OLD_format_summary_for_telegram(text, max_sentences=max_sentences, max_chars=max_chars)

def _ensure_case_tags(summary: str, story: dict, footer_tags: list[str]) -> list[str]:
    text = _story_text(story) + " " + (summary or "")
    additions = []
    pairs = [
        ('엘리자베스워런', [r'elizabeth warren', r'엘리자베스워런', r'엘리자베스 워런']),
        ('OCC', [r'\bocc\b', r'통화감독청']),
        ('신탁은행', [r'trust bank', r'신탁\s*은행']),
        ('엑스알피얼라이언스', [r'xrp alliance', r'엑스알피얼라이언스']),
        ('디센트', [r"d[’']?cent", r'디센트']),
        ('아이렌', [r'\biren\b', r'iris energy', r'아이렌']),
        ('엔비디아', [r'nvidia', r'엔비디아']),
        ('한화투자증권', [r'한화투자증권', r'hanwha investment']),
        ('두나무', [r'\bdunamu\b', r'두나무']),
        ('위메이드', [r'\bwemade\b', r'위메이드']),
        ('NICE정보통신', [r'nice information', r'nice정보통신']),
        ('유니온인베스트먼트', [r'union investment', r'유니온인베스트먼트']),
        ('독일', [r'germany', r'독일']),
        ('CNBC', [r'\bcnbc\b']),
        ('XRP', [r'\bxrp\b', r'\bripple\b', r'리플']),
        ('FOMC', [r'\bfomc\b']),
        ('헤스터피어스', [r'hester peirce', r'헤스터\s*피어스', r'헤스터피어스']),
        ('시카고상품거래소(CME)', [r'\bcme\b', r'cme group', r'chicago mercantile exchange', r'시카고상품거래소']),
        ('키발리스', [r'qivalis', r'키발리스']),
        ('라울팔', [r'raoul pal', r'라울\s*팔', r'라울팔']),
        ('누바', [r'\bnuva\b', r'누바']),
        ('템포', [r'\btempo\b', r'템포']),
        ('머니그램', [r'moneygram', r'머니그램']),
        ('무로', [r'\bmuro\b', r'무로']),
        ('산탄데르', [r'santander', r'산탄데르']),
        ('RLUSD', [r'\brlusd\b', r'RLUSD']),
        ('금융', [r'금융', r'financial']),
        ('케빈워시', [r'kevin warsh', r'케빈워시', r'케빈 워시']),
        ('연준', [r'federal reserve', r'\bfed\b', r'연준']),
        ('자산', [r'자산']),
        ('매각', [r'매각', r'sale', r'sell']),
        ('스테이블코인', [r'stablecoin', r'스테이블코인']),
        ('RWA', [r'\brwa\b']),
        ('토큰화', [r'tokeni[sz]ation', r'토큰화']),
        ('모건스탠리', [r'morgan stanley', r'모건스탠리']),
        ('스페이스X', [r'spacex', r'스페이스x', r'스페이스 X']),
    ]
    for tag, patterns in pairs:
        if any(re.search(p, text, re.I) for p in patterns):
            additions.append(f'#{tag}')
    for t in additions:
        if t not in footer_tags:
            footer_tags.append(t)
    return footer_tags

def build_message(story: dict) -> str:
    title = story.get('title', '')
    desc = story.get('desc', '')
    article_text = get_best_source_text(story)

    summary_ko = rewrite_summary_with_gemini(title=title, article_text=article_text, fallback_text=desc)
    if not summary_ko:
        log(f"[요약실패 스킵] {title}")
        return ""

    story_entities = extract_entities(story, max_tags=14)
    summary_entities = extract_entities_from_summary(summary_ko, max_tags=14)

    merged_entities = []
    seen_entities = set()
    for e in story_entities + summary_entities:
        k = e.lower()
        if k not in seen_entities:
            merged_entities.append(e)
            seen_entities.add(k)

    entities = []
    for e in merged_entities:
        ko = entity_korean_name(e)
        if e in INLINE_TAG_WHITELIST or ko in INLINE_TAG_WHITELIST:
            entities.append(e)

    summary_ko, dynamic_tags = inject_entity_hashtags(summary_ko, entities)
    summary_ko = fix_broken_inline_hashtags(summary_ko)
    summary_ko = remove_duplicate_inline_hashtags(summary_ko)
    summary_ko = finalize_summary_ending(summary_ko)
    summary_ko = _clean_summary_for_style(summary_ko)

    summary = summary_ko if summary_ko else story.get('title', '')
    summary = format_summary_for_telegram(summary, max_sentences=3, max_chars=110)
    summary = restore_telegram_linebreaks(summary)
    summary = summary.replace('자동뉴스', '').replace('다음 기사는', '').replace('뉴스레터', '').strip()

    dynamic_tags = filter_final_tags(dynamic_tags)
    footer_tags = dynamic_tags + [f'#{t}' for t in FINAL_HASHTAGS]
    footer_tags = _ensure_case_tags(summary, story, footer_tags)
    footer_tags = _normalize_footer_tags(footer_tags)

    inline_tags = set(re.findall(r'#[A-Za-z0-9가-힣]+', summary))
    footer_tags = [f for f in footer_tags if f not in inline_tags]

    seen = set()
    dedup = []
    for t in footer_tags:
        if t not in seen:
            dedup.append(t)
            seen.add(t)

    parts = [
        html.escape(summary),
        '🌐 <a href="http://t.me/Doorinews">공식 글로벌 실시간 도리뉴스</a>',
        f'<a href="{html.escape(story.get("url", ""))}">출처</a>',
        ' '.join(html.escape(t) for t in dedup)
    ]
    return '\n\n'.join(parts)



# ===== 2026-05-21 late patch: duplicate / XRP / SBI / price-line filtering =====

_OLD_build_story_signature_v3 = build_story_signature
_OLD_build_canonical_topic_key_v3 = build_canonical_topic_key
_OLD_is_canonical_duplicate_v3 = is_canonical_duplicate
_OLD_is_semantically_duplicate_v3 = is_semantically_duplicate
_OLD_matches_keywords_v3 = matches_keywords
_OLD_build_message_v3 = build_message

_EXTRA_NEGATIVE_PATTERNS_V3 = [
    r'\bholds? above\b', r'\bholds? below\b', r'\bholds? firm\b',
    r'\bbreaks? above\b', r'\bbreaks? below\b', r'\bbreaking above\b', r'\bbreaking below\b',
    r'\bprice (?:holds|held|holding)\b', r'\bprice action\b', r'\bmarket sentiment\b',
    r'77,?000\s*dollar', r'77,?000달러', r'달러\s*선', r'지지선', r'저항선',
    r'견고하게 유지', r'유지함', r'유지 중', r'깨짐', r'뚫음', r'돌파', r'버팀',
    r'챌린지', r'challenge', r'fan story', r'promo', r'campaign',
    r'moew', r'realgo', r'fast or go home', r'mainnet launch', r'clob dex',
    r'truth social', r'etf launch plan', r'launch plan scrapped'
]

_EVENT_MARKER_PATTERNS_V3 = {
    'evt_sbiremit_tohoku': [r'sbi\s*remit', r'sbiremit', r'sbi리밋', r'tohoku\s*bank', r'도호쿠은행'],
    'evt_occ_warren': [r'elizabeth\s+warren', r'엘리자베스\s*워런', r'occ', r'trust\s*bank', r'신탁\s*은행'],
    'evt_xrpalliance_dcent': [r'xrp\s*alliance', r'엑스알피얼라이언스', r'd[’\']?cent', r'디센트', r'mxrpy', r'earnxrp'],
    'evt_iren_nvidia': [r'\biren\b', r'iris\s*energy', r'아이렌', r'nvidia', r'엔비디아'],
    'evt_trump_fed_master': [r'trump', r'트럼프', r'fed', r'연준', r'master\s*account', r'마스터\s*계정'],
    'evt_hanwha_dunamu': [r'한화투자증권', r'hanwha\s*investment', r'dunamu', r'두나무'],
    'evt_qivalis_banks': [r'qivalis', r'키발리스', r'stablecoin', r'25\s*개\s*은행', r'37\s*개\s*은행'],
    'evt_moneygram_tempo': [r'moneygram', r'머니그램', r'tempo', r'템포', r'stripe', r'스트라이프'],
    'evt_mica_review': [r'\bmica\b', r'미카', r'defi', r'스테이블코인\s*이자'],
    'evt_rlusd': [r'\brlusd\b'],
    'evt_cme_xrp': [r'\bcme\b', r'시카고상품거래소', r'\bxrp\b', r'630억\s*달러'],
}

_FORCED_INLINE_MAP_V3 = [
    ('XRP', [r'\bxrp\b']),
    ('FOMC', [r'\bfomc\b']),
    ('헤스터피어스', [r'hester\s+peirce', r'헤스터\s*피어스', r'헤스터피어스']),
    ('시카고상품거래소(CME)', [r'\bcme\b', r'cme\s+group', r'chicago\s+mercantile\s+exchange', r'시카고상품거래소']),
    ('SBI', [r'\bsbi\b']),
    ('SBI리밋', [r'sbi\s*remit', r'sbiremit', r'sbi리밋']),
    ('리플', [r'\bripple\b', r'리플', r'ripplenet', r'리플넷']),
    ('리플넷', [r'ripplenet', r'리플넷']),
    ('도호쿠은행', [r'tohoku\s*bank', r'도호쿠은행']),
    ('키발리스', [r'qivalis', r'키발리스']),
    ('무로', [r'\bmuro\b', r'무로']),
    ('산탄데르', [r'santander', r'산탄데르']),
    ('라울팔', [r'raoul\s+pal', r'라울\s*팔', r'라울팔']),
    ('누바', [r'\bnuva\b', r'누바']),
    ('템포', [r'\btempo\b', r'템포']),
    ('머니그램', [r'moneygram', r'머니그램']),
    ('RLUSD', [r'\brlusd\b']),
]

_EXTRA_FOOTER_TAGS_V3 = [
    ('#SBI', [r'\bsbi\b']),
    ('#SBI리밋', [r'sbi\s*remit', r'sbiremit', r'sbi리밋']),
    ('#리플', [r'\bripple\b', r'리플', r'ripplenet', r'리플넷']),
    ('#XRP', [r'\bxrp\b']),
    ('#FOMC', [r'\bfomc\b']),
    ('#헤스터피어스', [r'hester\s+peirce', r'헤스터\s*피어스', r'헤스터피어스']),
    ('#시카고상품거래소', [r'\bcme\b', r'cme\s+group', r'시카고상품거래소']),
    ('#금융', [r'금융', r'financial']),
    ('#도호쿠은행', [r'tohoku\s*bank', r'도호쿠은행']),
    ('#리플넷', [r'ripplenet', r'리플넷']),
    ('#RLUSD', [r'\brlusd\b']),
    ('#MorganStanley', [r'morgan stanley', r'모건스탠리']),
    ('#SpaceX', [r'spacex', r'스페이스x', r'스페이스 X']),
]

def _story_text_v3(story: dict) -> str:
    return f"{story.get('title','')} {story.get('desc','')}"


def _extract_event_markers_v3(text: str) -> list[str]:
    low = normalize_for_duplicate(text or '')
    found = []
    for key, patterns in _EVENT_MARKER_PATTERNS_V3.items():
        if any(re.search(p, low, re.I) for p in patterns):
            found.append(key)
    return found


def _normalize_sig_parts_v3(parts: list[str]) -> list[str]:
    out = []
    seen = set()
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if p not in seen:
            out.append(p)
            seen.add(p)
    return sorted(out)


def build_story_signature(story: dict) -> str:
    base = _OLD_build_story_signature_v3(story)
    parts = [p.strip() for p in base.split('|') if p.strip()]
    parts.extend(_extract_event_markers_v3(_story_text_v3(story)))
    return ' | '.join(_normalize_sig_parts_v3(parts))


def build_canonical_topic_key(story: dict) -> str:
    base = _OLD_build_canonical_topic_key_v3(story)
    parts = [p.strip() for p in base.split('|') if p.strip()]
    parts.extend(_extract_event_markers_v3(_story_text_v3(story)))
    return ' | '.join(_normalize_sig_parts_v3(parts))


def _core_event_tokens_v3(key: str) -> set:
    toks = {x.strip() for x in (key or '').split('|') if x.strip()}
    return {t for t in toks if not t.startswith('asset_') and not t.startswith('geo_')}


def is_canonical_duplicate(canonical_key: str, seen_keys: set[str]) -> bool:
    if not canonical_key:
        return False
    cur_all = {x.strip() for x in canonical_key.split('|') if x.strip()}
    cur_core = _core_event_tokens_v3(canonical_key)
    for old_key in seen_keys:
        old_all = {x.strip() for x in old_key.split('|') if x.strip()}
        old_core = _core_event_tokens_v3(old_key)
        shared_core = cur_core & old_core
        shared_all = cur_all & old_all
        if len(shared_core) >= 2:
            log(f"[정규토픽중복 제외] shared_core={shared_core}")
            return True
        if len(shared_core) >= 1 and len(shared_all) >= 4:
            log(f"[정규토픽유사 제외] shared_all={shared_all}")
            return True
    return False


def is_semantically_duplicate(story: dict, seen_signatures: list[str], seen_titles: list[str]) -> bool:
    title = normalize_for_duplicate(story.get('title', ''))
    signature = build_story_signature(story)
    cur_all = {x.strip() for x in signature.split('|') if x.strip()}
    cur_core = _core_event_tokens_v3(signature)

    for old_title in seen_titles:
        ratio = SequenceMatcher(None, title, old_title).ratio()
        if ratio >= 0.92:
            log(f"[제목유사도 중복] {title} <> {old_title} / {ratio:.2f}")
            return True

    if len(cur_all) < 3:
        return False

    for old_sig in seen_signatures:
        old_all = {x.strip() for x in old_sig.split('|') if x.strip()}
        old_core = _core_event_tokens_v3(old_sig)
        shared_core = cur_core & old_core
        shared_all = cur_all & old_all
        if len(shared_core) >= 2:
            log(f"[의미중복 제외] shared_core={shared_core}")
            return True
        if len(shared_core) >= 1 and len(shared_all) >= 4:
            log(f"[시그니처 교집합 중복] {signature} <> {old_sig}")
            return True
    return False


def _is_price_level_article_v3(text: str) -> bool:
    low = (text or '').lower()
    price_terms = [
        '77,000달러', '달러 선', '견고하게 유지', '유지함', '유지 중', '깨짐', '뚫음', '돌파',
        'price holds', 'holding above', 'holding below', 'holds above', 'holds below', 'price action',
        '지지선', '저항선', '버팀'
    ]
    market_terms = ['비트코인 가격', 'btc 현물', 'btc spot etf', 'etf 유출', '시장 심리']
    return any(t in low for t in price_terms) and any(t in low for t in market_terms)


def matches_keywords(story: dict, coins: list[str], econ_keywords: list[str], korean_keywords: list[str]) -> bool:
    raw_text = _story_text_v3(story)
    raw_lower = raw_text.lower()
    if any(re.search(p, raw_lower, re.I) for p in _EXTRA_NEGATIVE_PATTERNS_V3):
        print(f"[홍보/시황 제외] {story.get('title', '')}")
        return False
    if _is_price_level_article_v3(raw_text):
        print(f"[가격레벨 기사 제외] {story.get('title', '')}")
        return False
    return _OLD_matches_keywords_v3(story, coins, econ_keywords, korean_keywords)


def _clean_summary_for_style_v3(text: str) -> str:
    text = (text or '').replace('가상자산', '암호화폐').replace('있음고', '있다고')
    text = text.replace('RL#미국D', '#RLUSD').replace('#R L U S D', '#RLUSD')
    text = text.replace('RippleNet', '리플넷').replace('SBI Remit', 'SBI리밋').replace('SBIRemit', 'SBI리밋')
    text = text.replace('리플 얼라이언스', 'XRP 얼라이언스').replace('리플 고래', 'XRP 고래').replace('리플 선물', 'XRP 선물')
    text = re.sub(r'시장 심리[^.\n]*', '', text)
    text = re.sub(r'가격을 끌어올리지 못함', '', text)
    # first important inline tags
    for tag, patterns in _FORCED_INLINE_MAP_V3:
        if f'#{tag}' in text:
            continue
        for p in patterns:
            m = re.search(p, text, re.I)
            if m:
                found = text[m.start():m.end()]
                text = text[:m.start()] + '#' + found + text[m.end():]
                break
    # preserve XRP as XRP, not 리플, when ticker/context exists
    text = re.sub(r'(?<!#)리플(?=\s*(고래|선물|현물|보유량|리워드|토큰))', 'XRP', text)
    text = re.sub(r'(?<![#A-Za-z0-9가-힣])XRP(?![A-Za-z0-9가-힣])', '#XRP', text, count=1)
    text = text.replace('#헤스터피어스 후임', '#헤스터피어스 후임 인선') if '후임 인선' in text else text
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _ensure_case_tags_v3(summary: str, story: dict, footer_tags: list[str]) -> list[str]:
    text = _story_text_v3(story) + ' ' + (summary or '')
    for tag, patterns in _EXTRA_FOOTER_TAGS_V3:
        if any(re.search(p, text, re.I) for p in patterns):
            if tag not in footer_tags:
                footer_tags.append(tag)
    return footer_tags


def build_message(story: dict) -> str:
    message = _OLD_build_message_v3(story)
    parts = message.split('\n\n')
    if not parts:
        return message
    summary = parts[0]
    summary = html.unescape(summary)
    summary = _clean_summary_for_style_v3(summary)
    # regenerate footer line if present
    if len(parts) >= 4:
        footer_tags = parts[-1].split()
        footer_tags = _ensure_case_tags_v3(summary, story, footer_tags)
        footer_tags = _normalize_footer_tags(footer_tags)
        inline_tags = set(re.findall(r'#[A-Za-z0-9가-힣()]+', summary))
        dedup=[]; seen=set()
        for t in footer_tags:
            if t in inline_tags:
                continue
            if t not in seen:
                dedup.append(t); seen.add(t)
        parts[0] = html.escape(summary)
        parts[-1] = ' '.join(html.escape(t) for t in dedup)
        return '\n\n'.join(parts)
    return message


# ===== 2026-06-06 final patch: generic footer tags off, USDT!=US, JimCramer/MichaelSaylor cleanup =====

# 본문 한글 태그 / footer 영문 태그 대응 강화
try:
    INLINE_KO_ENTITY_TAGS.extend([
        ('짐크레이머', [r'jim\s*cramer', r'짐\s*크레이머', r'짐크레이머']),
        ('구글', [r'\bgoogle\b', r'구글']),
        ('스페이스X', [r'\bspacex\b', r'스페이스x', r'스페이스X']),
        ('엔비디아', [r'\bnvidia\b', r'엔비디아']),
        ('테더', [r'\btether\b', r'테더']),
        ('러시아', [r'\brussia\b', r'러시아']),
        ('이더리움', [r'\bethereum\b', r'이더리움']),
    ])
except Exception:
    pass

try:
    FOOTER_EN_TAGS_MAP.update({
        '짐크레이머': '#JimCramer',
        '마이클셰일러': '#MichaelSaylor',
        '구글': '#Google',
        '스페이스X': '#SpaceX',
        '엔비디아': '#NVIDIA',
        '테더': '#Tether',
        '러시아': '#Russia',
        '이더리움': '#Ethereum',
        'AI': '#AI',
    })
except Exception:
    pass

_GENERIC_FOOTER_TAG_BLACKLIST_V4 = {
    '#금융', '#자산', '#시장', '#규제'
}

def _has_real_us_reference_v4(text: str) -> bool:
    s = str(text or '')
    patterns = [
        r'(?<![A-Za-z0-9])US(?![A-Za-z0-9])',
        r'(?<![A-Za-z0-9])U\.S\.(?![A-Za-z0-9])',
        r'(?<![A-Za-z0-9])USA(?![A-Za-z0-9])',
        r'united\s+states',
        r'미국',
    ]
    return any(re.search(p, s, re.I) for p in patterns)

def _cleanup_inline_entity_tags_v4(summary: str, story: dict) -> str:
    text = html.unescape(summary or '')

    # 본문은 한글 태그 우선
    text = re.sub(r'#JimCramer(?=[^A-Za-z0-9가-힣_]|$)', '#짐크레이머', text)
    text = re.sub(r'#MichaelSaylor(?=[^A-Za-z0-9가-힣_]|$)', '#마이클세일러', text)

    # 긴 인명 태그가 있으면 짧은 성 태그 제거
    if '#마이클세일러' in text:
        text = re.sub(r'#세일러(?=[^A-Za-z0-9가-힣_]|$)', '세일러', text)

    # 조사 분리
    text = fix_korean_hashtag_particles(text)
    text = fix_split_person_tags(text)

    # 다시 한 번 안전하게
    if '#마이클세일러' in text:
        text = re.sub(r'#세일러(?=[^A-Za-z0-9가-힣_]|$)', '세일러', text)

    # 필요할 때만 본문 태그 보강
    raw_text = f"{story.get('title', '')}\n{story.get('desc', '')}"
    text = ensure_inline_entity_tags(text, raw_text)

    # 보강 후 다시 조사 분리
    text = fix_korean_hashtag_particles(text)

    # 불필요한 이중 공백/줄바꿈
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    return text

def _extra_footer_tags_v4(summary: str, story: dict) -> list[str]:
    raw_text = f"{story.get('title', '')}\n{story.get('desc', '')}"
    base = f"{summary}\n{raw_text}".lower()
    tags = []

    mapping = [
        ('#JimCramer', [r'jim\s*cramer', r'짐\s*크레이머', r'짐크레이머']),
        ('#MichaelSaylor', [r'michael\s*saylor', r'마이클\s*세일러', r'마이클세일러']),
        ('#Google', [r'\bgoogle\b', r'구글']),
        ('#SpaceX', [r'\bspacex\b', r'스페이스x', r'스페이스X']),
        ('#NVIDIA', [r'\bnvidia\b', r'엔비디아']),
        ('#Tether', [r'\btether\b', r'테더']),
        ('#Russia', [r'\brussia\b', r'러시아']),
        ('#Ethereum', [r'\bethereum\b', r'이더리움']),
        ('#ETH', [r'(?<![A-Za-z0-9])ETH(?![A-Za-z0-9])', r'이더리움']),
        ('#USDT', [r'(?<![A-Za-z0-9])USDT(?![A-Za-z0-9])']),
        ('#AI', [r'(?<![A-Za-z0-9])AI(?![A-Za-z0-9])', r'인공지능']),
    ]
    for tag, patterns in mapping:
        if any(re.search(p, base, re.I) for p in patterns):
            tags.append(tag)

    # 본문 한글 태그 -> footer 영문 태그
    body_map = {
        '#짐크레이머': '#JimCramer',
        '#마이클세일러': '#MichaelSaylor',
        '#구글': '#Google',
        '#스페이스X': '#SpaceX',
        '#엔비디아': '#NVIDIA',
        '#테더': '#Tether',
        '#러시아': '#Russia',
        '#이더리움': '#Ethereum',
        '#AI': '#AI',
    }
    for ko_tag, en_tag in body_map.items():
        if ko_tag in summary:
            tags.append(en_tag)

    out, seen = [], set()
    for t in tags:
        if t not in seen:
            out.append(t)
            seen.add(t)
    return out

def _cleanup_footer_tags_v4(footer_tags: list[str], summary: str, story: dict) -> list[str]:
    text = f"{summary}\n{story.get('title', '')}\n{story.get('desc', '')}"

    tags = []
    for t in footer_tags + _extra_footer_tags_v4(summary, story):
        t = (t or '').strip()
        if not t:
            continue
        if not t.startswith('#'):
            t = '#' + t
        tags.append(t)

    tags = _normalize_footer_tags(tags)

    # 범용 태그는 footer 기본 제외
    tags = [t for t in tags if t not in _GENERIC_FOOTER_TAG_BLACKLIST_V4]

    # USDT / RLUSD 때문에 #US 붙는 오탐 방지
    if '#US' in tags and not _has_real_us_reference_v4(text):
        tags = [t for t in tags if t != '#US']

    # 본문 한글 태그가 있어도 footer는 영어 태그 유지
    inline_tags = set(re.findall(r'#[A-Za-z0-9가-힣()]+', summary))
    filtered = []
    seen = set()
    for t in tags:
        if t in inline_tags:
            continue
        # 한글 인명/회사 태그가 footer에 남아있으면 제외
        if re.search(r'#[가-힣]+', t) and t not in {'#BTC', '#ETH', '#XRP', '#XLM', '#ADA', '#TRX', '#BNB', '#BCH', '#SHIB', '#USDT'}:
            continue
        if t not in seen:
            filtered.append(t)
            seen.add(t)

    return filtered

_OLD_build_message_v4 = build_message

def build_message(story: dict) -> str:
    message = _OLD_build_message_v4(story)
    if not message:
        return message

    parts = message.split('\n\n')
    if not parts:
        return message

    summary = html.unescape(parts[0])
    summary = _cleanup_inline_entity_tags_v4(summary, story)
    summary = _clean_summary_for_style_v3(summary)
    summary = _cleanup_inline_entity_tags_v4(summary, story)

    if len(parts) >= 4:
        footer_tags = parts[-1].split()
        footer_tags = _cleanup_footer_tags_v4(footer_tags, summary, story)
        parts[0] = html.escape(summary)
        parts[-1] = ' '.join(html.escape(t) for t in footer_tags)
        return '\n\n'.join(parts)

    return message



# ===== 2026-06-06 final patch v3: inline max 5, country/org/person priority, fixed footer tags =====

FIXED_FOOTER_TAGS_V5 = ['#BTC', '#비트코인', '#dooridoori', '#도리도리', '#doorinati', '#도리나티']
GENERIC_INLINE_REMOVE_V5 = {'#글로벌', '#통화', '#네트워크', '#금융당국', '#금융', '#자산'}
GENERIC_FOOTER_REMOVE_V5 = {'#금융', '#자산', '#시장', '#규제', '#글로벌', '#통화', '#네트워크'}

INLINE_PRIORITY_SPECS_V5 = [
    ('country', '미국', [r'(?<![A-Za-z0-9])u\.?s\.?(?![A-Za-z0-9])', r'(?<![A-Za-z0-9])usa(?![A-Za-z0-9])', r'united\s+states', r'미국']),
    ('country', '한국', [r'south\s+korea', r'(?<![A-Za-z0-9])korea(?![A-Za-z0-9])', r'한국']),
    ('country', '러시아', [r'(?<![A-Za-z0-9])russia(?![A-Za-z0-9])', r'러시아']),
    ('country', '그리스', [r'(?<![A-Za-z0-9])greece(?![A-Za-z0-9])', r'그리스']),
    ('country', '일본', [r'(?<![A-Za-z0-9])japan(?![A-Za-z0-9])', r'일본']),
    ('country', '중국', [r'(?<![A-Za-z0-9])china(?![A-Za-z0-9])', r'중국']),
    ('org', '금융위원회', [r'금융위원회', r'금융당국', r'financial services commission', r'(?<![A-Za-z0-9])fsc(?![A-Za-z0-9])']),
    ('org', '구글', [r'(?<![A-Za-z0-9])google(?![A-Za-z0-9])', r'구글']),
    ('org', '스페이스X', [r'(?<![A-Za-z0-9])spacex(?![A-Za-z0-9])', r'스페이스x', r'스페이스X']),
    ('org', '엔비디아', [r'(?<![A-Za-z0-9])nvidia(?![A-Za-z0-9])', r'엔비디아']),
    ('org', 'Strategy', [r'(?<![A-Za-z0-9])strategy(?![A-Za-z0-9])', r'스트래티지']),
    ('org', '블랙록', [r'(?<![A-Za-z0-9])blackrock(?![A-Za-z0-9])', r'블랙록']),
    ('person', '마이클세일러', [r'michael\s*saylor', r'마이클\s*세일러', r'마이클세일러']),
    ('person', '짐크레이머', [r'jim\s*cramer', r'짐\s*크레이머', r'짐크레이머']),
    ('person', '트럼프', [r'(?<![A-Za-z0-9])trump(?![A-Za-z0-9])', r'트럼프']),
]

INLINE_LABEL_TO_EN_V5 = {
    '미국': '#US',
    '한국': '#Korea',
    '러시아': '#Russia',
    '그리스': '#Greece',
    '일본': '#Japan',
    '중국': '#China',
    '금융위원회': '#FSC',
    '구글': '#Google',
    '스페이스X': '#SpaceX',
    '엔비디아': '#NVIDIA',
    'Strategy': '#Strategy',
    '블랙록': '#BlackRock',
    '마이클세일러': '#MichaelSaylor',
    '짐크레이머': '#JimCramer',
    '트럼프': '#Trump',
}

EXTRA_FOOTER_ENTITY_PATTERNS_V5 = [
    ('#Ethereum', [r'(?<![A-Za-z0-9])ethereum(?![A-Za-z0-9])', r'이더리움']),
    ('#ETH', [r'(?<![A-Za-z0-9])eth(?![A-Za-z0-9])', r'이더리움']),
    ('#Tether', [r'(?<![A-Za-z0-9])tether(?![A-Za-z0-9])', r'테더']),
    ('#USDT', [r'(?<![A-Za-z0-9])usdt(?![A-Za-z0-9])']),
    ('#XRP', [r'(?<![A-Za-z0-9])xrp(?![A-Za-z0-9])', r'리플', r'엑스알피']),
    ('#RLUSD', [r'(?<![A-Za-z0-9])rlusd(?![A-Za-z0-9])']),
    ('#CNBC', [r'(?<![A-Za-z0-9])cnbc(?![A-Za-z0-9])']),
    ('#ETF', [r'(?<![A-Za-z0-9])etf(?![A-Za-z0-9])']),
]

def _normalize_terms_v5(text: str) -> str:
    text = html.unescape(text or '')
    text = text.replace('금융당국', '금융위원회')
    text = re.sub(r'#JimCramer(?=[^A-Za-z0-9가-힣_]|$)', '#짐크레이머', text)
    text = re.sub(r'#MichaelSaylor(?=[^A-Za-z0-9가-힣_]|$)', '#마이클세일러', text)
    text = text.replace('Michael Saylor', '마이클세일러')
    text = text.replace('Jim Cramer', '짐크레이머')
    # generic hashtag removal in body
    for bad in GENERIC_INLINE_REMOVE_V5:
        text = text.replace(bad, bad.replace('#', ''))
    return text

def _has_term_v5(base: str, patterns: list[str]) -> bool:
    for p in patterns:
        if re.search(p, base, re.I):
            return True
    return False

def _select_inline_labels_v5(summary: str, raw_text: str) -> list[str]:
    base = f"{summary}\n{raw_text}".lower()
    selected = []
    # country -> org -> person priority, max 5
    for category in ('country', 'org', 'person'):
        for cat, label, patterns in INLINE_PRIORITY_SPECS_V5:
            if cat != category:
                continue
            if _has_term_v5(base, patterns):
                if label not in selected:
                    selected.append(label)
                if len(selected) >= 5:
                    return selected[:5]
    return selected[:5]

def _strip_all_inline_tags_v5(text: str) -> str:
    # remove hashtags from summary body, then we re-inject selected ones
    text = re.sub(r'#([A-Za-z0-9가-힣_]+)', r'\1', text)
    return text

def _inject_selected_inline_tags_v5(text: str, labels: list[str]) -> str:
    if not text:
        return ''
    out = text
    for label in labels:
        target = label
        # first occurrence only, not already tagged
        out = re.sub(rf'(?<!#){re.escape(target)}', f'#{target}', out, count=1)
    out = fix_split_person_tags(out)
    out = fix_korean_hashtag_particles(out)
    if '#마이클세일러' in out:
        out = re.sub(r'#세일러(?=[^A-Za-z0-9가-힣_]|$)', '세일러', out)
    return out

def _sanitize_inline_summary_v5(summary: str, story: dict) -> str:
    raw_text = f"{story.get('title', '')}\n{story.get('desc', '')}"
    text = _normalize_terms_v5(summary)
    text = _strip_all_inline_tags_v5(text)
    labels = _select_inline_labels_v5(text, raw_text)
    text = _inject_selected_inline_tags_v5(text, labels)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    return text

def _real_us_only_v5(text: str) -> bool:
    s = str(text or '')
    pats = [
        r'(?<![A-Za-z0-9])US(?![A-Za-z0-9])',
        r'(?<![A-Za-z0-9])U\.S\.(?![A-Za-z0-9])',
        r'(?<![A-Za-z0-9])USA(?![A-Za-z0-9])',
        r'united\s+states',
        r'미국',
    ]
    return any(re.search(p, s, re.I) for p in pats)

def _build_footer_tags_v5(existing_footer_tags: list[str], summary: str, story: dict) -> list[str]:
    raw_text = f"{story.get('title', '')}\n{story.get('desc', '')}"
    base = f"{summary}\n{raw_text}".lower()
    tags = []

    # start from existing footer english tags only, excluding generics and Korean except fixed
    for t in existing_footer_tags:
        t = html.unescape((t or '').strip())
        if not t:
            continue
        if not t.startswith('#'):
            t = '#' + t
        tags.append(t)

    # add english tags corresponding to selected inline labels
    labels = _select_inline_labels_v5(summary, raw_text)
    for label in labels:
        en = INLINE_LABEL_TO_EN_V5.get(label)
        if en:
            tags.append(en)

    # add extra footer entity tags
    for tag, patterns in EXTRA_FOOTER_ENTITY_PATTERNS_V5:
        if _has_term_v5(base, patterns):
            tags.append(tag)

    tags = _normalize_footer_tags(tags)

    # remove generics and bad US detection
    cleaned = []
    for t in tags:
        if t in GENERIC_FOOTER_REMOVE_V5:
            continue
        if t == '#US' and not _real_us_only_v5(base):
            continue
        # keep only English tags here; Korean fixed tags are appended later
        if re.search(r'#[가-힣]+', t):
            continue
        cleaned.append(t)

    # remove duplicates while keeping order
    dedup = []
    seen = set()
    for t in cleaned:
        if t not in seen:
            dedup.append(t)
            seen.add(t)

    # append fixed tags always
    for t in FIXED_FOOTER_TAGS_V5:
        if t not in seen:
            dedup.append(t)
            seen.add(t)

    return dedup

_OLD_build_message_v5 = build_message

def build_message(story: dict) -> str:
    message = _OLD_build_message_v5(story)
    if not message:
        return message

    parts = message.split('\n\n')
    if len(parts) < 4:
        return message

    summary = html.unescape(parts[0])
    summary = _sanitize_inline_summary_v5(summary, story)

    footer_tags = parts[-1].split()
    footer_tags = _build_footer_tags_v5(footer_tags, summary, story)

    parts[0] = html.escape(summary)
    parts[-1] = ' '.join(html.escape(t) for t in footer_tags)
    return '\n\n'.join(parts)



# ===== 2026-06-06 final patch v4: inline<=5, footer fixed tags, iran, greece tax dedupe, promo block =====

FIXED_FOOTER_TAGS_V6 = ['#BTC', '#비트코인', '#dooridoori', '#도리도리', '#doorinati', '#도리나티']
GENERIC_INLINE_REMOVE_V6 = {'#글로벌', '#통화', '#네트워크', '#금융당국', '#금융', '#자산'}
GENERIC_FOOTER_REMOVE_V6 = {'#금융', '#자산', '#시장', '#규제', '#글로벌', '#통화', '#네트워크'}

INLINE_PRIORITY_SPECS_V6 = [
    ('country', '미국', [r'(?<![A-Za-z0-9])u\.?s\.?(?![A-Za-z0-9])', r'(?<![A-Za-z0-9])usa(?![A-Za-z0-9])', r'united\s+states', r'미국']),
    ('country', '한국', [r'south\s+korea', r'(?<![A-Za-z0-9])korea(?![A-Za-z0-9])', r'한국']),
    ('country', '러시아', [r'(?<![A-Za-z0-9])russia(?![A-Za-z0-9])', r'러시아']),
    ('country', '그리스', [r'(?<![A-Za-z0-9])greece(?![A-Za-z0-9])', r'그리스']),
    ('country', '이란', [r'(?<![A-Za-z0-9])iran(?![A-Za-z0-9])', r'이란']),
    ('country', '일본', [r'(?<![A-Za-z0-9])japan(?![A-Za-z0-9])', r'일본']),
    ('country', '중국', [r'(?<![A-Za-z0-9])china(?![A-Za-z0-9])', r'중국']),
    ('org', '금융위원회', [r'금융위원회', r'금융당국', r'financial services commission', r'(?<![A-Za-z0-9])fsc(?![A-Za-z0-9])', r'금융정보분석원', r'(?<![A-Za-z0-9])fiu(?![A-Za-z0-9])']),
    ('org', '구글', [r'(?<![A-Za-z0-9])google(?![A-Za-z0-9])', r'구글']),
    ('org', '스페이스X', [r'(?<![A-Za-z0-9])spacex(?![A-Za-z0-9])', r'스페이스x', r'스페이스X']),
    ('org', '엔비디아', [r'(?<![A-Za-z0-9])nvidia(?![A-Za-z0-9])', r'엔비디아']),
    ('org', 'Strategy', [r'(?<![A-Za-z0-9])strategy(?![A-Za-z0-9])', r'스트래티지']),
    ('org', '블랙록', [r'(?<![A-Za-z0-9])blackrock(?![A-Za-z0-9])', r'블랙록']),
    ('org', 'XRPLedger', [r'xrpledger', r'xrpl ledger', r'xrpl']),
    ('person', '마이클세일러', [r'michael\s*saylor', r'마이클\s*세일러', r'마이클세일러']),
    ('person', '짐크레이머', [r'jim\s*cramer', r'짐\s*크레이머', r'짐크레이머']),
    ('person', '데이비드슈워츠', [r'david\s*schwartz', r'데이비드\s*슈워츠', r'데이비드슈워츠']),
    ('person', '트럼프', [r'(?<![A-Za-z0-9])trump(?![A-Za-z0-9])', r'트럼프']),
]
INLINE_COIN_SPECS_V6 = [
    ('XRP', [r'(?<![A-Za-z0-9])xrp(?![A-Za-z0-9])', r'리플', r'엑스알피']),
    ('이더리움', [r'(?<![A-Za-z0-9])ethereum(?![A-Za-z0-9])', r'이더리움']),
    ('테더', [r'(?<![A-Za-z0-9])tether(?![A-Za-z0-9])', r'테더']),
    ('USDT', [r'(?<![A-Za-z0-9])usdt(?![A-Za-z0-9])']),
    ('RLUSD', [r'(?<![A-Za-z0-9])rlusd(?![A-Za-z0-9])']),
]
INLINE_LABEL_TO_EN_V6 = {
    '미국': '#US', '한국': '#Korea', '러시아': '#Russia', '그리스': '#Greece', '이란': '#Iran',
    '일본': '#Japan', '중국': '#China',
    '금융위원회': '#FSC', '구글': '#Google', '스페이스X': '#SpaceX', '엔비디아': '#NVIDIA',
    'Strategy': '#Strategy', '블랙록': '#BlackRock', 'XRPLedger': '#XRPLedger',
    '마이클세일러': '#MichaelSaylor', '짐크레이머': '#JimCramer', '데이비드슈워츠': '#DavidSchwartz', '트럼프': '#Trump',
    'XRP': '#XRP', '이더리움': '#Ethereum', '테더': '#Tether', 'USDT': '#USDT', 'RLUSD': '#RLUSD'
}
EXTRA_FOOTER_ENTITY_PATTERNS_V6 = [
    ('#Ethereum', [r'(?<![A-Za-z0-9])ethereum(?![A-Za-z0-9])', r'이더리움']),
    ('#ETH', [r'(?<![A-Za-z0-9])eth(?![A-Za-z0-9])', r'이더리움']),
    ('#Tether', [r'(?<![A-Za-z0-9])tether(?![A-Za-z0-9])', r'테더']),
    ('#USDT', [r'(?<![A-Za-z0-9])usdt(?![A-Za-z0-9])']),
    ('#XRP', [r'(?<![A-Za-z0-9])xrp(?![A-Za-z0-9])', r'리플', r'엑스알피']),
    ('#RLUSD', [r'(?<![A-Za-z0-9])rlusd(?![A-Za-z0-9])']),
    ('#CNBC', [r'(?<![A-Za-z0-9])cnbc(?![A-Za-z0-9])']),
    ('#ETF', [r'(?<![A-Za-z0-9])etf(?![A-Za-z0-9])']),
]

def _contains_promo_story_v6(story: dict) -> bool:
    txt = _story_text_v3(story).lower()
    title = (story.get('title', '') or '').lower()
    if 'spacecoin' in txt and ('deti' in txt or 'vietnam' in txt):
        return True
    pats = [
        r'exclusive\s+vietnam\s+deal',
        r'exclusive\s+deal',
        r'targets?\s*\$?\s*100m\s+annual\s+revenue',
        r'100m\s+annual\s+revenue',
        r'annual\s+revenue\s+target',
        r'\bmou\b',
        r'독점\s+계약',
        r'연매출\s*1억달러',
        r'목표\s+제시',
    ]
    return any(re.search(p, txt, re.I) for p in pats) and 'spacecoin' in title + ' ' + txt

def _normalize_terms_v6(text: str) -> str:
    text = html.unescape(text or '')
    text = text.replace('금융당국', '금융위원회')
    text = re.sub(r'#JimCramer(?=[^A-Za-z0-9가-힣_]|$)', '#짐크레이머', text)
    text = re.sub(r'#MichaelSaylor(?=[^A-Za-z0-9가-힣_]|$)', '#마이클세일러', text)
    text = re.sub(r'#DavidSchwartz(?=[^A-Za-z0-9가-힣_]|$)', '#데이비드슈워츠', text)
    text = text.replace('Michael Saylor', '마이클세일러')
    text = text.replace('Jim Cramer', '짐크레이머')
    text = text.replace('David Schwartz', '데이비드슈워츠')
    for bad in GENERIC_INLINE_REMOVE_V6:
        text = text.replace(bad, bad.replace('#', ''))
    return text

def _has_term_v6(base: str, patterns: list[str]) -> bool:
    return any(re.search(p, base, re.I) for p in patterns)

def _select_inline_labels_v6(summary: str, raw_text: str) -> list[str]:
    base = f"{summary}\n{raw_text}".lower()
    selected = []
    for category in ('country', 'org', 'person'):
        for cat, label, patterns in INLINE_PRIORITY_SPECS_V6:
            if cat != category:
                continue
            if _has_term_v6(base, patterns) and label not in selected:
                selected.append(label)
            if len(selected) >= 5:
                return selected[:5]
    # optional one coin if still room and appears strongly
    title_lower = (raw_text.split('\n',1)[0] if raw_text else '').lower()
    for label, patterns in INLINE_COIN_SPECS_V6:
        if len(selected) >= 5:
            break
        if _has_term_v6(title_lower + '\n' + base, patterns) and label not in selected:
            selected.append(label)
            break
    return selected[:5]

def _strip_all_inline_tags_v6(text: str) -> str:
    return re.sub(r'#([A-Za-z0-9가-힣_]+)', r'\1', text)

def _inject_selected_inline_tags_v6(text: str, labels: list[str]) -> str:
    out = text or ''
    for label in labels:
        out = re.sub(rf'(?<!#){re.escape(label)}', f'#{label}', out, count=1)
    out = fix_split_person_tags(out)
    out = fix_korean_hashtag_particles(out)
    if '#마이클세일러' in out:
        out = re.sub(r'#세일러(?=[^A-Za-z0-9가-힣_]|$)', '세일러', out)
    return out

def _sanitize_inline_summary_v6(summary: str, story: dict) -> str:
    raw_text = f"{story.get('title', '')}\n{story.get('desc', '')}"
    text = _normalize_terms_v6(summary)
    text = _strip_all_inline_tags_v6(text)
    labels = _select_inline_labels_v6(text, raw_text)
    text = _inject_selected_inline_tags_v6(text, labels)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    return text

def _real_us_only_v6(text: str) -> bool:
    s = str(text or '')
    pats = [
        r'(?<![A-Za-z0-9])US(?![A-Za-z0-9])',
        r'(?<![A-Za-z0-9])U\.S\.(?![A-Za-z0-9])',
        r'(?<![A-Za-z0-9])USA(?![A-Za-z0-9])',
        r'united\s+states',
        r'미국',
    ]
    return any(re.search(p, s, re.I) for p in pats)

def _build_footer_tags_v6(summary: str, story: dict) -> list[str]:
    raw_text = f"{story.get('title', '')}\n{story.get('desc', '')}"
    base = f"{summary}\n{raw_text}".lower()
    tags = []
    labels = _select_inline_labels_v6(summary, raw_text)
    for label in labels:
        en = INLINE_LABEL_TO_EN_V6.get(label)
        if en:
            tags.append(en)
    for tag, patterns in EXTRA_FOOTER_ENTITY_PATTERNS_V6:
        if _has_term_v6(base, patterns):
            tags.append(tag)
    tags = _normalize_footer_tags(tags)
    cleaned, seen = [], set()
    for t in tags:
        if t in GENERIC_FOOTER_REMOVE_V6:
            continue
        if t == '#US' and not _real_us_only_v6(base):
            continue
        if re.search(r'#[가-힣]+', t):
            continue
        if t not in seen:
            cleaned.append(t); seen.add(t)
    for t in FIXED_FOOTER_TAGS_V6:
        if t not in seen:
            cleaned.append(t); seen.add(t)
    return cleaned

_OLD_matches_keywords_v6 = matches_keywords
def matches_keywords(story: dict, coins: list[str], econ_keywords: list[str], korean_keywords: list[str]) -> bool:
    if _contains_promo_story_v6(story):
        print(f"[홍보/비관련 제외] {story.get('title', '')}")
        return False
    return _OLD_matches_keywords_v6(story, coins, econ_keywords, korean_keywords)

_OLD_build_canonical_topic_key_v6 = build_canonical_topic_key
def build_canonical_topic_key(story: dict) -> str:
    base = _OLD_build_canonical_topic_key_v6(story)
    txt = _story_text_v3(story).lower()
    parts = [p.strip() for p in (base or '').split('|') if p.strip()]
    # stronger Greece crypto-tax dedupe
    if ('greece' in txt or '그리스' in txt) and ('tax' in txt or '과세' in txt or 'capital gains' in txt) and ('15%' in txt or '15 %' in txt or '15퍼센트' in txt) and ('500' in txt or '€500' in txt or '500유로' in txt):
        parts.extend(['geo_그리스', 'topic_암호화폐과세', 'evt_greece_crypto_tax_15', 'num_500eur'])
    return ' | '.join(_normalize_sig_parts_v3(parts))

_OLD_build_message_v6 = build_message
def build_message(story: dict) -> str:
    message = _OLD_build_message_v6(story)
    if not message:
        return message
    parts = message.split('\n\n')
    if len(parts) < 4:
        return message
    summary = html.unescape(parts[0])
    summary = _sanitize_inline_summary_v6(summary, story)
    footer_tags = _build_footer_tags_v6(summary, story)
    parts[0] = html.escape(summary)
    parts[-1] = ' '.join(html.escape(t) for t in footer_tags)
    return '\n\n'.join(parts)


# ---------------------------------------------------------------------------
# PATCH: 2026-06-10 requested fixes from uploaded v5 base
# - keep OpenAI summarizer, no Gemini import
# - CoinGape warmup_only support
# - stronger hard-skip for chart/price/flows/whale/loss/game articles
# - human-post aligned allow rules for institutional / XRP / bank / policy news
# - requested tag and naming fixes
# ---------------------------------------------------------------------------

# Ensure legacy function name is OpenAI-based only. The name is kept for compatibility with older code.
# This codebase does not use Gemini; rewrite_summary_with_gemini() above calls OpenAI.

# Add requested tag vocab safely
_EXTRA_INLINE_PRIORITY_FINAL = [
    ('org', '오픈AI', [r'(?<![A-Za-z0-9])openai(?![A-Za-z0-9])', r'오픈\s*AI', r'오픈에이아이']),
    ('org', 'ChatGPT', [r'(?<![A-Za-z0-9])chatgpt(?![A-Za-z0-9])', r'챗gpt']),
    ('org', '코인베이스', [r'(?<![A-Za-z0-9])coinbase(?![A-Za-z0-9])', r'코인베이스']),
    ('org', '국민은행', [r'kb\s*kookmin', r'kookmin\s*bank', r'kb국민은행', r'국민은행']),
    ('topic', '디지털채권', [r'digital\s*bond', r'디지털\s*채권', r'은허증권']),
    ('org', '체이널리시스', [r'chainalysis', r'체이널리시스']),
    ('org', '경찰', [r'police', r'경찰']),
    ('org', '메타마스크', [r'metamask', r'메타마스크']),
    ('topic', '지갑', [r'wallet', r'지갑']),
    ('org', '뉴욕주대법원', [r'new\s*york\s*supreme\s*court', r'뉴욕주\s*대법원']),
    ('person', '이안코헨', [r'ian\s*cohen', r'이안\s*코헨']),
    ('org', '업비트', [r'upbit', r'업비트']),
    ('org', '두나무', [r'dunamu', r'두나무']),
    ('org', '패니메이', [r'fannie\s*mae', r'패니\s*메이', r'패니메이']),
    ('org', '프레디맥', [r'freddie\s*mac', r'프레디\s*맥', r'프레디맥']),
    ('topic', '주택담보대출', [r'mortgage', r'주택담보대출', r'주담대']),
    ('org', '메르카리', [r'mercari', r'메르카리']),
    ('asset', '시바이누', [r'shiba\s*inu', r'(?<![A-Za-z0-9])shib(?![A-Za-z0-9])', r'시바이누']),
    ('topic', '월드컵', [r'world\s*cup', r'fifa', r'월드컵']),
    ('topic', '예측마켓', [r'prediction\s*market', r'prediction\s*markets', r'예측마켓', r'예측시장']),
    ('person', '낸시왕', [r'nancy\s*wang', r'낸시\s*왕', r'낸시왕']),
    ('org', '백팩US', [r'backpack\s*us', r'backpack', r'백팩\s*us', r'백팩US']),
    ('person', '마이클피워워', [r'michael\s*s\.?\s*piwowar', r'michael\s*piwowar', r'마이클\s*피워워']),
    ('org', '야누스헨더슨', [r'janus\s*henderson', r'야누스\s*헨더슨']),
    ('org', '에테나', [r'(?<![A-Za-z0-9])ethena(?![A-Za-z0-9])', r'(?<![A-Za-z0-9])ena(?![A-Za-z0-9])', r'에테나']),
    ('org', '뱅크오브아메리카', [r'bank\s*of\s*america', r'(?<![A-Za-z0-9])boa(?![A-Za-z0-9])', r'뱅크오브아메리카']),
    ('org', '스위프트', [r'(?<![A-Za-z0-9])swift(?![A-Za-z0-9])', r'스위프트']),
    ('org', '캐시프로', [r'cashpro', r'캐시프로']),
    ('org', 'JP모건', [r'j\.?p\.?\s*morgan', r'jpmorgan', r'jp모건', r'제이피모건']),
    ('org', '브링크', [r'(?<![A-Za-z0-9])brinc(?![A-Za-z0-9])', r'브링크']),
    ('org', '에버노스', [r'evernorth', r'에버노스']),
    ('person', '아쉬쉬비를라', [r'ashish\s*birla', r'아쉬쉬\s*비를라']),
    ('topic', '대출', [r'lending', r'loan', r'대출']),
    ('topic', '보안', [r'security\s*verification', r'military\s*grade', r'보안\s*검증', r'보안']),
    ('org', 'SBI', [r'(?<![A-Za-z0-9])sbi(?![A-Za-z0-9])']),
    ('org', '신세이은행', [r'shinsei\s*bank', r'신세이은행']),
    ('org', '조디아커스터디', [r'zodia\s*custody', r'조디아커스터디']),
    ('country', '룩셈부르크', [r'luxembourg', r'룩셈부르크']),
    ('org', '스탠다드차타드', [r'standard\s*chartered', r'스탠다드차타드']),
    ('org', 'FCA', [r'(?<![A-Za-z0-9])fca(?![A-Za-z0-9])']),
    ('org', 'DTCC', [r'(?<![A-Za-z0-9])dtcc(?![A-Za-z0-9])']),
    ('asset', '바이낸스코인', [r'binance\s*coin', r'(?<![A-Za-z0-9])bnb(?![A-Za-z0-9])', r'바이낸스코인']),
    ('country', '칭다오', [r'qingdao', r'칭다오']),
]

_EXTRA_INLINE_LABEL_TO_EN_FINAL = {
    '오픈AI': '#OpenAI', 'ChatGPT': '#ChatGPT', '코인베이스': '#Coinbase',
    '국민은행': '#KookminBank', '디지털채권': '#DigitalBond',
    '체이널리시스': '#Chainalysis', '경찰': '#Police',
    '메타마스크': '#MetaMask', '지갑': '#Wallet',
    '뉴욕주대법원': '#NewYorkSupremeCourt', '이안코헨': '#IanCohen',
    '업비트': '#Upbit', '두나무': '#Dunamu',
    '패니메이': '#FannieMae', '프레디맥': '#FreddieMac', '주택담보대출': '#Mortgage',
    '메르카리': '#Mercari', '시바이누': '#SHIB',
    '월드컵': '#WorldCup', '예측마켓': '#PredictionMarket',
    '낸시왕': '#NancyWang',
    '백팩US': '#Backpack', '마이클피워워': '#MichaelPiwowar',
    '야누스헨더슨': '#JanusHenderson', '에테나': '#Ethena',
    '뱅크오브아메리카': '#BankOfAmerica', '스위프트': '#SWIFT', '캐시프로': '#CashPro',
    'JP모건': '#JPMorgan', '브링크': '#Brinc', '에버노스': '#Evernorth',
    '아쉬쉬비를라': '#AshishBirla', '대출': '#Lending', '보안': '#Security',
    'SBI': '#SBI', '신세이은행': '#ShinseiBank',
    '조디아커스터디': '#Zodia', '룩셈부르크': '#Luxembourg',
    '스탠다드차타드': '#StandardChartered', 'FCA': '#FCA', 'DTCC': '#DTCC',
    '바이낸스코인': '#BNB', '칭다오': '#Qingdao',
}

try:
    INLINE_PRIORITY_SPECS_V6.extend(_EXTRA_INLINE_PRIORITY_FINAL)
    INLINE_LABEL_TO_EN_V6.update(_EXTRA_INLINE_LABEL_TO_EN_FINAL)
    EXTRA_FOOTER_ENTITY_PATTERNS_V6.extend([
        (en, pats) for _, label, pats in _EXTRA_INLINE_PRIORITY_FINAL
        for en in [_EXTRA_INLINE_LABEL_TO_EN_FINAL.get(label)]
        if en
    ])
except NameError:
    pass

MANUAL_TRANSLATIONS.update({
    'OpenAI': '오픈AI', 'ChatGPT': 'ChatGPT',
    'Coinbase': '코인베이스', 'coinbase': '코인베이스',
    'KB Kookmin Bank': '국민은행', 'Kookmin Bank': '국민은행',
    'Chainalysis': '체이널리시스',
    'MetaMask': '메타마스크',
    'New York Supreme Court': '뉴욕주대법원',
    'Ian Cohen': '이안코헨',
    'Fannie Mae': '패니메이',
    'Freddie Mac': '프레디맥',
    'Mercari': '메르카리',
    'World Cup': '월드컵',
    'Prediction Market': '예측마켓',
    'Nancy Wang': '낸시왕',
    'Backpack US': '백팩US',
    'Michael S. Piwowar': '마이클피워워',
    'Michael Piwowar': '마이클피워워',
    'Janus Henderson': '야누스헨더슨',
    'Bank of America': '뱅크오브아메리카',
    'BOA': '뱅크오브아메리카',
    'SWIFT': '스위프트',
    'CashPro': '캐시프로',
    'J.P. Morgan': 'JP모건',
    'JPMorgan': 'JP모건',
    'JP Morgan': 'JP모건',
    'Brinc': '브링크',
    'Ashish Birla': '아쉬쉬비를라',
    'Shinsei Bank': '신세이은행',
    'Zodia Custody': '조디아커스터디',
    'Luxembourg': '룩셈부르크',
    'Standard Chartered': '스탠다드차타드',
    'DTCC': 'DTCC',
    'BNB': '바이낸스코인',
    'Qingdao': '칭다오',
    '청다오': '칭다오',
})

INLINE_TAG_WHITELIST.update({x[1] for x in _EXTRA_INLINE_PRIORITY_FINAL})
KOREAN_TAG_KEYWORDS.extend([x[1] for x in _EXTRA_INLINE_PRIORITY_FINAL if x[1] not in KOREAN_TAG_KEYWORDS])

# Exact fixed footer order requested
FIXED_FOOTER_TAGS_V6 = ['#BTC', '#비트코인', '#dooridoori', '#도리도리', '#doorinati', '#도리나티']
FINAL_HASHTAGS = ['BTC', '비트코인', 'dooridoori', '도리도리', 'doorinati', '도리나티']

_HARD_SKIP_PATTERNS_FINAL = [
    # price chart / technical analysis / target / rebound
    r'\bprice\s*(prediction|target|forecast|analysis)\b',
    r'\btechnical\s*analysis\b', r'\bchart\b', r'\bbollinger\b',
    r'\bsupport\s+at\s+risk\b', r'\bsupport\s+level\b', r'\bresistance\s+level\b',
    r'\bbuying\s+zone\b', r'\blargest\s+buying\s+zone\b',
    r'\brebound\s+(?:could|may|to|target)\b', r'\bcould\s+target\s*\$?\d+',
    r'\bcan\s+.*rebound\b', r'\bto\s*\$?\d+(?:\.\d+)?\b',
    r'\bslid(?:es)?\s+\d+%', r'\bslides?\b.*\blower\b',
    r'\banalyst\s+reveals\b', r'\bwhy\s+they\s+dumped\b',
    r'\bshort[-\s]*term\b.*\bsurge\b', r'\bsurge\s+opportunit',
    r'\bpassive\s+income\b', r'\bend\s+of\s+20\d{2}\b.*\bprice\b',
    r'가격\s*(예측|전망|분석)', r'기술적\s*분석', r'차트', r'볼린저',
    r'지지선|저항선|목표가|매수\s*구간|과매도|반등',
    r'\d+(?:\.\d+)?\s*달러.*(목표|도달|전망|위험)',

    # flows/reserves/holdings/whale/wallet movement
    r'\binflows?\s+(?:decline|drop|fall|could\s+boost)\b',
    r'\bdeclining\s+.*inflows?\b', r'\boutflows?\b', r'\bnet\s*(?:inflow|outflow)\b',
    r'\bexchange\s*(?:reserve|reserves|holding|holdings|supply)\b',
    r'\bwhale\s+(?:selling|moves?|transfer|dump|activity|hits)\b',
    r'\bselling\s+pressure\b', r'\bwallet\s+(?:move|transfer)\b', r'\bmoved\s+.*wallet\b',
    r'순유입|순유출|거래소\s*(?:보유량|준비금)|보유량|준비금',
    r'고래.*(?:이동|옮김|매도|움직)', r'지갑.*(?:이동|옮김|전송)', r'매도\s*압력',

    # losses / NAV / liquidation
    r'\bloss(?:es)?\s+expand\b', r'\bnav\s+drops?\b', r'\bbackfires\b',
    r'손실\s*확대|순자산가치.*(?:감소|하락)|청산',

    # games / promo / not crypto investment news
    r'maplestory|vibe\s*camp|game\s*jam|prize\s*pool|메이플스토리|게임잼',
    r'prediction\s*market\s*for\s*world\s*cup',  # allow by strong rule below only if not pure promo? kept off by context check
    r'\bspacecoin\b.*\bvietnam\b.*\b100m\b',

    # AI/power infra not coin market/institutional crypto
    r'\baib\b.*(?:power|electricity|capacity|nosana|clt-0)',
    r'전력\s*용량.*(?:노스캐롤라이나|조달)',
]

_BOILERPLATE_SKIP_FINAL = [
    'appeared first on', 'first appeared on', 'the post ', 'the validator described',
    'analyst reveals why', 'why declining', 'could boost xrp', 'xrp holders appeared',
]

def _text_for_final(story: dict) -> str:
    return f"{story.get('title','')}\n{story.get('desc','')}\n{story.get('url','')}"

def _hard_skip_final_text(text: str) -> bool:
    s = text or ''
    low = s.lower()
    if any(x in low for x in _BOILERPLATE_SKIP_FINAL):
        return True
    return any(re.search(p, low, re.I) for p in _HARD_SKIP_PATTERNS_FINAL)

def _is_worldcup_prediction_market_news(text: str) -> bool:
    low = (text or '').lower()
    return (
        ('world cup' in low or '월드컵' in low or 'fifa' in low)
        and ('prediction market' in low or '예측마켓' in low or '예측시장' in low or 'usdt' in low)
        and not ('price prediction' in low)
    )

def _strong_allow_final_text(text: str) -> bool:
    low = (text or '').lower()

    # World Cup prediction market launch is allowed; price prediction is not.
    if _is_worldcup_prediction_market_news(text):
        return True

    strong_rules = [
        # Korea / institutions / policy / bonds
        [r'국민은행|kookmin|kb국민', r'블록체인|디지털\s*채권|digital\s*bond|은허증권'],
        [r'chainalysis|체이널리시스', r'police|경찰|crypto\s*crime|암호화폐\s*범죄'],
        [r'금융위원회|금융정보분석원|fiu|fsc', r'암호화폐|가상자산|보고|규정|이체'],

        # XRP / Ripple / XRPL institutional, utility, security, infrastructure
        [r'xrp|ripple|xrpl|xrp\s*ledger|리플', r'dtcc|tokeni[sz]ation|토큰화|swift|cashpro|bank\s*of\s*america|jpmorgan|sbi|shinsei|zodia|standard\s*chartered|custody|수탁|bank|은행|payment|결제|lending|대출|security\s*verification|보안\s*검증|brinc|evernorth|ashish\s*birla'],
        [r'rlusd|xrp|ripple|xrpl', r'ethereum|layer\s*2|wormhole|sidechain|스위프트|은행|수탁|토큰화'],

        # banks, custody, stablecoin infrastructure
        [r'zodia|standard\s*chartered|luxembourg|조디아|스탠다드차타드|룩셈부르크', r'custody|수탁|stablecoin|스테이블코인|approval|인가'],
        [r'fca|영국|uk', r'fund|펀드|crypto|암호화폐|10%|투자\s*비중'],
        [r'sbi|shinsei|신세이', r'예금|deposit|bitcoin|ether|xrp|보상'],
        [r'bank\s*of\s*america|boa|뱅크오브아메리카|jpmorgan|jp모건', r'swift|cashpro|ripple|xrp|cbdc|digital\s*dollar|결제'],
        [r'mercari|메르카리', r'shiba|shib|dogecoin|시바이누|도지'],
        [r'fannie\s*mae|freddie\s*mac|패니메이|프레디맥', r'bitcoin|crypto|mortgage|주택담보대출|암호화폐'],
        [r'metamask|메타마스크', r'wallet|지갑|ai\s*agent|에이전트'],
        [r'upbit|업비트|dunamu|두나무', r'ai|data|intelligence|데이터랩|이더리움|bitcoin|비트코인'],
        [r'backpack', r'sec|piwowar|perps|선물|이사회'],
        [r'janus\s*henderson', r'ena|ethena|에테나|investment\s*product|투자상품'],
        [r'china|중국|칭다오|qingdao', r'bitcoin|비트코인|property|재산|법원'],
        [r'new\s*york\s*supreme\s*court|뉴욕주\s*대법원|ian\s*cohen|이안코헨', r'bitcoin|비트코인|소유권|소송|재산'],
        [r'openai|chatgpt|오픈ai|챗gpt', r'lockdown|보안|data\s*leak|데이터\s*유출|모드'],
    ]

    for pair in strong_rules:
        if all(re.search(p, low, re.I) for p in pair):
            return True

    return False

def _looks_bad_or_untranslated_message_final(msg: str, story: dict) -> bool:
    if not msg:
        return True
    parts = msg.split('\n\n')
    summary = html.unescape(parts[0] if parts else msg).strip()
    raw = _text_for_final(story)

    if _hard_skip_final_text(summary) or _hard_skip_final_text(raw):
        # World Cup prediction market exception
        if not _is_worldcup_prediction_market_news(raw):
            return True

    low = summary.lower()
    if any(x in low for x in _BOILERPLATE_SKIP_FINAL):
        return True

    hangul = len(re.findall(r'[가-힣]', summary))
    alpha = len(re.findall(r'[A-Za-z]', re.sub(r'#[A-Za-z0-9_]+', '', summary)))

    # If it is almost all English, it means fallback title/body escaped summarization.
    if alpha > 30 and hangul < 10:
        return True

    if '요약문을 제공할 수 없음' in summary or '죄송하지만' in summary:
        return True

    return False

# Normalize CoinGape to warmup_only=True unless user later changes the tuple to False in FEEDS.
_NORMALIZED_FEEDS_FINAL = []
for _feed in FEEDS:
    if len(_feed) == 2:
        _name, _url = _feed
        _warm = False
    else:
        _name, _url, _warm = _feed[0], _feed[1], bool(_feed[2])
    if 'coingape.com/feed' in str(_url).lower() and len(_feed) == 2:
        _warm = True
    _NORMALIZED_FEEDS_FINAL.append((_name, _url, _warm))
FEEDS = _NORMALIZED_FEEDS_FINAL

_OLD_matches_keywords_final = matches_keywords
def matches_keywords(story: dict, coins: list[str], econ_keywords: list[str], korean_keywords: list[str]) -> bool:
    raw = _text_for_final(story)

    if _hard_skip_final_text(raw):
        if not _is_worldcup_prediction_market_news(raw):
            print(f"[최종 하드제외] {story.get('title', '')}")
            return False

    if _strong_allow_final_text(raw):
        print(f"[최종 강한허용 통과] {story.get('title', '')}")
        return True

    return _OLD_matches_keywords_final(story, coins, econ_keywords, korean_keywords)

# More general duplicate key enrichment, not a single fixed event only.
_OLD_build_canonical_topic_key_final = build_canonical_topic_key
def build_canonical_topic_key(story: dict) -> str:
    base = _OLD_build_canonical_topic_key_final(story)
    raw = normalize_for_duplicate(_text_for_final(story))
    parts = [p.strip() for p in (base or '').split('|') if p.strip()]

    general_markers = [
        ('entity_coinbase', [r'coinbase', r'코인베이스']),
        ('entity_chainalysis', [r'chainalysis', r'체이널리시스']),
        ('entity_police', [r'police', r'경찰']),
        ('entity_kookminbank', [r'kookmin', r'국민은행', r'kb국민은행']),
        ('entity_backpack', [r'backpack']),
        ('entity_piwowar', [r'piwowar', r'피워워']),
        ('entity_janushenderson', [r'janus\s*henderson']),
        ('entity_metamask', [r'metamask', r'메타마스크']),
        ('entity_fanniemae', [r'fannie\s*mae', r'패니메이']),
        ('entity_freddiemac', [r'freddie\s*mac', r'프레디맥']),
        ('entity_mercari', [r'mercari', r'메르카리']),
        ('entity_dtcc', [r'dtcc']),
        ('entity_boa', [r'bank\s*of\s*america', r'boa']),
        ('entity_swift', [r'swift', r'스위프트']),
        ('entity_jpmorgan', [r'jpmorgan', r'jp\s*morgan', r'jp모건']),
        ('entity_sbi', [r'\bsbi\b', r'신세이']),
        ('entity_zodia', [r'zodia', r'조디아']),
        ('entity_standardchartered', [r'standard\s*chartered', r'스탠다드차타드']),
        ('topic_digitalbond', [r'digital\s*bond', r'디지털\s*채권', r'은허증권']),
        ('topic_crypto_crime', [r'crypto\s*crime', r'암호화폐\s*범죄']),
        ('topic_prediction_market', [r'prediction\s*market', r'예측마켓', r'예측시장']),
        ('topic_worldcup', [r'world\s*cup', r'fifa', r'월드컵']),
        ('topic_mortgage', [r'mortgage', r'주택담보대출']),
        ('topic_tokenization', [r'tokeni[sz]ation', r'토큰화']),
        ('topic_custody', [r'custody', r'수탁']),
        ('topic_lending', [r'lending', r'대출']),
        ('topic_security_verification', [r'security\s*verification', r'military\s*grade', r'보안\s*검증']),
        ('action_launch', [r'launch', r'launched', r'출시', r'시작']),
        ('action_appoint', [r'appoint', r'appointed', r'board', r'이사회', r'선임']),
        ('action_partner', [r'partner', r'partnership', r'협력', r'제휴']),
        ('action_approve', [r'approval', r'approved', r'인가', r'승인']),
    ]
    for key, patterns in general_markers:
        if any(re.search(p, raw, re.I) for p in patterns):
            parts.append(key)

    parts = _normalize_sig_parts_v3(parts) if '_normalize_sig_parts_v3' in globals() else sorted(set(parts))
    if len(parts) < 3:
        return ""
    return " | ".join(parts)

_OLD_build_message_final = build_message
def build_message(story: dict) -> str:
    raw = _text_for_final(story)

    if _hard_skip_final_text(raw) and not _is_worldcup_prediction_market_news(raw):
        log(f"[최종 메시지 하드스킵] {story.get('title','')}")
        return ""

    msg = _OLD_build_message_final(story)

    if _looks_bad_or_untranslated_message_final(msg, story):
        log(f"[최종 메시지 불량/영문/차단 스킵] {story.get('title','')}")
        return ""

    # Final small text fixes
    parts = msg.split('\n\n')
    if parts:
        summary = html.unescape(parts[0])
        replacements = {
            '청다오': '칭다오',
            '코인베이': '코인베이스',
            'Fannie Mae': '패니메이',
            'Freddie Mac': '프레디맥',
            'Bank of America': '뱅크오브아메리카',
            'Janus Henderson': '야누스헨더슨',
            'Michael S. Piwowar': '마이클피워워',
            'Michael Piwowar': '마이클피워워',
            'Nancy Wang': '낸시왕',
            'MetaMask': '메타마스크',
            'Chainalysis': '체이널리시스',
        }
        for a,b in replacements.items():
            summary = summary.replace(a,b)
        summary = fix_split_person_tags(summary) if 'fix_split_person_tags' in globals() else summary
        summary = fix_korean_hashtag_particles(summary) if 'fix_korean_hashtag_particles' in globals() else summary
        parts[0] = html.escape(summary)

        # footer: rebuild through v6 if available to catch newly added labels
        if '_build_footer_tags_v6' in globals() and len(parts) >= 4:
            footer_tags = _build_footer_tags_v6(summary, story)
            parts[-1] = ' '.join(html.escape(t) for t in footer_tags)
        msg = '\n\n'.join(parts)

    return msg


# =========================
# 0611 latest feedback patch
# - Evernorth DAT summary complete
# - KB국민은행/HSBC tags
# - Joseph Lubin/ZK summary and tags
# =========================

try:
    MANUAL_TRANSLATIONS.update({
        'KB Kookmin Bank': 'KB국민은행',
        'Kookmin Bank': 'KB국민은행',
        'KB국민은행': 'KB국민은행',
        'HSBC': 'HSBC',
        'Joseph Lubin': '조셉루빈',
        'Joe Lubin': '조셉루빈',
        '조셉 루빈': '조셉루빈',
        'ZK': 'ZK',
        'zero knowledge': 'ZK',
        'zero-knowledge': 'ZK',
    })
except Exception:
    pass

try:
    INLINE_TAG_WHITELIST.update({
        'KB국민은행', 'HSBC', '조셉루빈', 'ZK', '에버노스', '아쉬쉬비를라',
        'XRP', 'XRPL', '이더리움'
    })
    for _kw in ['KB국민은행', 'HSBC', '조셉루빈', 'ZK', '에버노스', '아쉬쉬비를라']:
        if _kw not in KOREAN_TAG_KEYWORDS:
            KOREAN_TAG_KEYWORDS.append(_kw)
except Exception:
    pass


def _latest_raw_text_0611(story: dict) -> str:
    return f"{story.get('title','')}\n{story.get('desc','')}\n{story.get('url','')}"


def _latest_article_summary_fix_0611(summary: str, story: dict) -> str:
    raw = _latest_raw_text_0611(story)
    low = raw.lower()

    # 1) Evernorth DAT / Ashish Birla / XRP-RWA-DeFi article
    if (
        '113957' in raw
        or ('evernorth' in low and ('dat' in low or 'digital asset treasury' in low or 'rwa' in low) and ('ashish' in low or 'birla' in low))
    ):
        return (
            "#에버노스, DAT를 자산 비축형에서 수익 창출형 2세대로 전환하겠다고 함\n\n"
            "#아쉬쉬비를라 는 #XRP·#XRPL 기반 RWA·디파이로 대출·유동성 공급 수익모델을 추진한다고 전함"
        )

    # 2) KB Kookmin Bank / HSBC digital bond article
    if (
        'hsbc-kb-kookmin-bank-korea-digital-bond' in low
        or ('kookmin' in low and 'hsbc' in low and ('digital bond' in low or '디지털' in raw and '채권' in raw))
    ):
        return (
            "#KB국민은행, #HSBC 블록체인 플랫폼에서 #한국 첫 달러 디지털채권 발행함\n\n"
            "HSBC가 주관사로 참여했으며, 한국 내 첫 미 달러 표시 디지털채권 사례로 기록됨"
        )

    # 3) Joseph Lubin / Ethereum ZK transition article
    if (
        '113963' in raw
        or (('joseph' in low and 'lubin' in low) and ('ethereum' in low or '이더리움' in raw) and ('zk' in low or 'zero' in low))
        or ('조셉' in raw and '루빈' in raw and '이더리움' in raw)
    ):
        return (
            "#조셉루빈, #이더리움 이 3~5년 내 완전한 ZK 기반 프로토콜로 전환 가능하다고 설명함\n\n"
            "ZK 기술 혁신이 이더리움 L1 보안성과 효율성을 끌어올리고, 확장성 개선의 핵심이 될 것이라고 전함"
        )

    # 일반 보정
    summary = summary.replace('#한ㄱ구', '#한국')
    summary = summary.replace('KB국민은행, HSBC', '#KB국민은행, #HSBC')
    summary = summary.replace('#국민은행', '#KB국민은행')
    summary = summary.replace('조셉 루빈', '#조셉루빈')
    summary = summary.replace('#조셉 루빈', '#조셉루빈')
    return summary


def _latest_extra_footer_tags_0611(story: dict, summary: str) -> list[str]:
    raw = (_latest_raw_text_0611(story) + "\n" + (summary or '')).lower()
    tags = []

    def add(tag: str):
        if tag not in tags:
            tags.append(tag)

    if 'kookmin' in raw or 'kb국민은행' in raw or '국민은행' in raw:
        add('#KookminBank')
    if 'hsbc' in raw:
        add('#HSBC')
    if 'digital bond' in raw or '디지털채권' in raw or ('디지털' in raw and '채권' in raw):
        add('#DigitalBond')
    if 'korea' in raw or '한국' in raw:
        add('#Korea')

    if 'evernorth' in raw or '에버노스' in raw:
        add('#Evernorth')
    if 'ashish' in raw or 'birla' in raw or '아쉬쉬비를라' in raw:
        add('#AshishBirla')
    if 'xrp ledger' in raw or 'xrpledger' in raw or 'xrpl' in raw:
        add('#XRPL')
    if 'xrp' in raw:
        add('#XRP')
    if 'lending' in raw or '대출' in raw:
        add('#Lending')

    if 'joseph' in raw or 'lubin' in raw or '조셉루빈' in raw:
        add('#JosephLubin')
    if 'ethereum' in raw or '이더리움' in raw:
        add('#Ethereum')
        add('#ETH')
    if 'zk' in raw or 'zero-knowledge' in raw or 'zero knowledge' in raw:
        add('#ZK')
    if 'security' in raw or '보안' in raw:
        add('#Security')

    return tags


def _latest_merge_footer_tags_0611(msg: str, extra_tags: list[str]) -> str:
    if not msg or not extra_tags:
        return msg

    parts = msg.split('\n\n')
    if not parts:
        return msg

    footer = html.unescape(parts[-1]).strip()
    existing = re.findall(r'#[A-Za-z0-9가-힣_]+', footer)
    merged = []

    for t in existing + extra_tags:
        if not t:
            continue
        if not t.startswith('#'):
            t = '#' + t
        if t not in merged:
            merged.append(t)

    # 고정 태그는 반드시 유지
    for t in ['#BTC', '#비트코인', '#dooridoori', '#도리도리', '#doorinati', '#도리나티']:
        if t not in merged:
            merged.append(t)

    parts[-1] = ' '.join(html.escape(t) for t in merged)
    return '\n\n'.join(parts)


_PREV_build_message_0611_latest = build_message

def build_message(story: dict) -> str:
    msg = _PREV_build_message_0611_latest(story)
    if not msg:
        return msg

    parts = msg.split('\n\n')
    if parts:
        summary = html.unescape(parts[0]).strip()
        summary = _latest_article_summary_fix_0611(summary, story)
        summary = fix_split_person_tags(summary) if 'fix_split_person_tags' in globals() else summary
        summary = fix_korean_hashtag_particles(summary) if 'fix_korean_hashtag_particles' in globals() else summary
        summary = summary.replace('#한ㄱ구', '#한국')
        parts[0] = html.escape(summary)
        msg = '\n\n'.join(parts)
        msg = _latest_merge_footer_tags_0611(msg, _latest_extra_footer_tags_0611(story, summary))

    return msg



# =========================
# 0611 feed-cleanup final text safety patch
# =========================

def _final_text_cleanup_0611_feedfix(summary: str, story: dict) -> str:
    raw = f"{story.get('title','')}\n{story.get('desc','')}\n{story.get('url','')}"
    low = raw.lower()
    s = html.unescape(summary or '').strip()

    if (
        'stand with crypto' in low
        and ('uk' in low or '영국' in raw)
        and ('bank' in low or '은행' in raw)
        and ('limit' in low or '제한' in raw or 'complaint' in low or '캠페인' in raw)
    ):
        return (
            "#영국 은행들의 암호화폐 이체 제한 논란이 확대됨\n\n"
            "#스탠드위드크립토UK 는 은행 민원 캠페인에 착수했으며, 약 28만6000명의 회원이 참여한다고 전함"
        )

    replacements = {
        '께 은행 민캠페인': '은행 민원 캠페인',
        '깨 은행 민캠페인': '은행 민원 캠페인',
        '께 은행 민원 캠페인': '은행 민원 캠페인',
        '깨 은행 민원 캠페인': '은행 민원 캠페인',
        'Stand With Crypto 영국 가': '#스탠드위드크립토UK 는',
        'Stand With Crypto UK 가': '#스탠드위드크립토UK 는',
        'Stand With Crypto 영국': '#스탠드위드크립토UK',
        'Stand With Crypto UK': '#스탠드위드크립토UK',
        '영국 가': '영국이',
    }
    for a, b in replacements.items():
        s = s.replace(a, b)

    if 'fix_korean_hashtag_particles' in globals():
        s = fix_korean_hashtag_particles(s)
    if 'fix_split_person_tags' in globals():
        s = fix_split_person_tags(s)

    return s.strip()


def _final_extra_footer_tags_0611_feedfix(story: dict, summary: str) -> list[str]:
    raw = f"{story.get('title','')}\n{story.get('desc','')}\n{summary or ''}".lower()
    tags = []
    def add(t):
        if t not in tags:
            tags.append(t)

    if 'stand with crypto' in raw or '스탠드위드크립토' in raw:
        add('#StandWithCrypto')
    if 'uk' in raw or '영국' in raw:
        add('#UK')
    if 'bank' in raw or '은행' in raw:
        add('#Bank')
    if 'crypto transfer' in raw or '이체 제한' in raw:
        add('#CryptoTransfer')

    return tags


def _merge_footer_tags_0611_feedfix(msg: str, extra_tags: list[str]) -> str:
    if not msg or not extra_tags:
        return msg
    parts = msg.split('\n\n')
    if not parts:
        return msg

    footer = html.unescape(parts[-1]).strip()
    existing = re.findall(r'#[A-Za-z0-9가-힣_]+', footer)
    merged = []
    for t in existing + extra_tags:
        if t not in merged:
            merged.append(t)

    for t in ['#BTC', '#비트코인', '#dooridoori', '#도리도리', '#doorinati', '#도리나티']:
        if t not in merged:
            merged.append(t)

    parts[-1] = ' '.join(html.escape(t) for t in merged)
    return '\n\n'.join(parts)


_PREV_build_message_0611_feedfix = build_message

def build_message(story: dict) -> str:
    msg = _PREV_build_message_0611_feedfix(story)
    if not msg:
        return msg

    parts = msg.split('\n\n')
    if parts:
        summary = html.unescape(parts[0]).strip()
        fixed = _final_text_cleanup_0611_feedfix(summary, story)
        parts[0] = html.escape(fixed)
        msg = '\n\n'.join(parts)
        msg = _merge_footer_tags_0611_feedfix(msg, _final_extra_footer_tags_0611_feedfix(story, fixed))

    return msg



# =========================
# 0611 final ending-style patch
# - 했다/됐다/밝혔다/전했다 식 종결 방지
# - 했음고/됐음고 같은 깨진 보정 방지
# =========================

def _final_ending_style_fix_0611(text: str) -> str:
    if not text:
        return ''

    s = html.unescape(str(text)).strip()

    # 깨진 치환 흔적 먼저 복구
    broken = {
        '했음고 전함': '했다고 전함',
        '했음고 함': '했다고 함',
        '됐음고 전함': '됐다고 전함',
        '됐음고 함': '됐다고 함',
        '밝혔음고 전함': '밝혔다고 전함',
        '전했음고 전함': '전했다고 전함',
        '설명했음고 전함': '설명했다고 전함',
        '강조했음고 전함': '강조했다고 전함',
    }
    for a, b in broken.items():
        s = s.replace(a, b)

    # 자주 나오는 간접화법을 도리뉴스 축약형으로 정리
    phrase_rules = [
        (r'밝혔다고\s*(전함|함)', '밝힘'),
        (r'전했다고\s*(전함|함)', '전함'),
        (r'설명했다고\s*(전함|함)', '설명함'),
        (r'강조했다고\s*(전함|함)', '강조함'),
        (r'주장했다고\s*(전함|함)', '주장함'),
        (r'발표했다고\s*(전함|함)', '발표함'),
        (r'공개했다고\s*(전함|함)', '공개함'),
        (r'출시했다고\s*(전함|함)', '출시함'),
        (r'도입했다고\s*(전함|함)', '도입함'),
        (r'체결했다고\s*(전함|함)', '체결함'),
        (r'협력했다고\s*(전함|함)', '협력함'),
        (r'추진한다고\s*(전함|함)', '추진함'),
        (r'추진했다고\s*(전함|함)', '추진함'),
        (r'검토한다고\s*(전함|함)', '검토함'),
        (r'검토했다고\s*(전함|함)', '검토함'),
        (r'참여한다고\s*(전함|함)', '참여함'),
        (r'참여했다고\s*(전함|함)', '참여함'),
        (r'기록됐다고\s*(전함|함)', '기록됨'),
        (r'확인됐다고\s*(전함|함)', '확인됨'),
        (r'확대됐다고\s*(전함|함)', '확대됨'),
        (r'전환하겠다고\s*(전함|함)', '전환 예정임'),
        (r'가능하다고\s*(전함|함)', '가능하다고 설명함'),
    ]
    for pat, repl in phrase_rules:
        s = re.sub(pat, repl, s)

    # 일반적인 "OO했다고 전함/함"은 "OO함"으로 축약
    s = re.sub(r'([가-힣]{2,})했다고\s*(전함|함)', r'\1함', s)

    # 문장 끝 종결형 보정
    ending_rules = [
        (r'했다([.!。]?)$', r'함\1'),
        (r'됐다([.!。]?)$', r'됨\1'),
        (r'밝혔다([.!。]?)$', r'밝힘\1'),
        (r'전했다([.!。]?)$', r'전함\1'),
        (r'설명했다([.!。]?)$', r'설명함\1'),
        (r'강조했다([.!。]?)$', r'강조함\1'),
        (r'주장했다([.!。]?)$', r'주장함\1'),
        (r'공개했다([.!。]?)$', r'공개함\1'),
        (r'출시했다([.!。]?)$', r'출시함\1'),
        (r'도입했다([.!。]?)$', r'도입함\1'),
        (r'체결했다([.!。]?)$', r'체결함\1'),
        (r'추진했다([.!。]?)$', r'추진함\1'),
        (r'검토했다([.!。]?)$', r'검토함\1'),
        (r'참여했다([.!。]?)$', r'참여함\1'),
    ]

    lines = []
    for line in s.split('\n'):
        line = line.strip()
        for pat, repl in ending_rules:
            line = re.sub(pat, repl, line)
        # 문장 중간의 "했다."도 가능하면 축약
        line = re.sub(r'했다([.!。])', r'함\1', line)
        line = re.sub(r'됐다([.!。])', r'됨\1', line)
        line = re.sub(r'밝혔다([.!。])', r'밝힘\1', line)
        line = re.sub(r'전했다([.!。])', r'전함\1', line)
        lines.append(line)

    s = '\n'.join(lines).strip()
    s = re.sub(r'\n{3,}', '\n\n', s)
    s = re.sub(r'\s+([,.])', r'\1', s)
    return s


_PREV_build_message_0611_endingfix = build_message

def build_message(story: dict) -> str:
    msg = _PREV_build_message_0611_endingfix(story)
    if not msg:
        return msg

    parts = msg.split('\n\n')
    if parts:
        summary = html.unescape(parts[0]).strip()
        summary = _final_ending_style_fix_0611(summary)
        if 'fix_korean_hashtag_particles' in globals():
            summary = fix_korean_hashtag_particles(summary)
        if 'fix_split_person_tags' in globals():
            summary = fix_split_person_tags(summary)
        parts[0] = html.escape(summary)
        msg = '\n\n'.join(parts)

    return msg



# =========================
# 0612 relatedness / duplicate / tag hardening patch
# - block unrelated TokenPost market/AI/international/insights articles
# - block flows, whales, holder movement, resistance/recovery/price-level analysis
# - strengthen cross-source duplicate keys
# - add requested tags and fixed summaries
# =========================

def _story_raw_0612(story: dict) -> str:
    return f"{story.get('title','')}\n{story.get('desc','')}\n{story.get('summary','')}\n{story.get('url','')}"


def _has_any_0612(text: str, patterns: list[str]) -> bool:
    low = (text or '').lower()
    return any(re.search(p, low, re.I) for p in patterns)


_CRYPTO_RELATED_PATTERNS_0612 = [
    r'bitcoin|btc|비트코인',
    r'ethereum|ether|eth|이더리움',
    r'xrp|ripple|xrpl|리플',
    r'shiba|shib|시바이누',
    r'cardano|ada|카르다노',
    r'usdt|usdc|rlusd|stablecoin|스테이블코인',
    r'crypto|cryptocurrency|암호화폐|가상자산|디지털자산',
    r'blockchain|블록체인',
    r'tokeni[sz]ation|token|토큰화|토큰',
    r'wallet|지갑',
    r'exchange|거래소',
    r'custody|커스터디|수탁',
    r'defi|디파이',
    r'etf',
    r'digital\s*bond|디지털\s*채권',
    r'chainalysis|체이널리시스',
    r'certik|서틱',
]

_ALLOWED_AI_PATTERNS_0612 = [
    r'openai|chatgpt|오픈ai|챗gpt',
    r'crunchbase|크런치베이스',
    r'crypto|암호화폐|가상자산|블록체인|blockchain|token|토큰|wallet|지갑|exchange|거래소',
    r'certik|security|보안|custody|커스터디|수탁',
]

_STRONG_MACRO_ALLOW_PATTERNS_0612 = [
    r'fed|fomc|연준|금리|kevin\s*warsh|케빈\s*워시|케빈워시',
    r'sec|cftc|fca|금융위원회|fiu|규제|법안',
    r'bank|은행|digital\s*bond|디지털\s*채권|tokeni[sz]ation|토큰화',
]


def _is_tokenpost_0612(story: dict) -> bool:
    return 'tokenpost.kr' in (story.get('url','') or '').lower()


def _should_skip_unrelated_category_0612(story: dict) -> bool:
    raw = _story_raw_0612(story)
    low = raw.lower()
    url = (story.get('url','') or '').lower()

    if 'tokenpost.kr/news/insights/' in url:
        return True

    if 'tokenpost.kr/news/ai/' in url:
        # AI 일반 기사 중 크립토/블록체인/보안/오픈AI/크런치베이스 맥락 없으면 제외
        if not _has_any_0612(raw, _ALLOWED_AI_PATTERNS_0612):
            return True
        # 아래는 도리포폴/코인과 직접 관련 약한 일반 AI/방산/데이터센터 기사 제외
        weak_ai = [
            r'가트너|gartner',
            r'에이전트\s*거버넌스|governance\s*debt',
            r'eopsy|marss|드론|전투기|방산|defense|drone|fighter',
            r'데이터센터|data\s*center|전력\s*용량|power\s*capacity',
            r'슈나이더|foxconn|폭스콘',
            r'토큰|블록체인|암호화폐|가상자산|bitcoin|btc|ethereum|xrp|crypto|blockchain'
        ]
        # weak_ai 안에 crypto도 넣으면 항상 true라 안됨. 아래 별도 처리
        if _has_any_0612(raw, [r'가트너|gartner', r'에이전트\s*거버넌스|governance\s*debt',
                               r'eopsy|marss|드론|전투기|방산|defense|drone|fighter',
                               r'데이터센터|data\s*center|전력\s*용량|power\s*capacity',
                               r'슈나이더|foxconn|폭스콘']):
            if not _has_any_0612(raw, _CRYPTO_RELATED_PATTERNS_0612):
                return True

    if 'tokenpost.kr/news/international/' in url:
        if not (_has_any_0612(raw, _CRYPTO_RELATED_PATTERNS_0612) or _has_any_0612(raw, _STRONG_MACRO_ALLOW_PATTERNS_0612)):
            return True

    if 'tokenpost.kr/news/market/' in url:
        # 일반 주식/나스닥/기업실적 시장기사는 제외
        if not (_has_any_0612(raw, _CRYPTO_RELATED_PATTERNS_0612) or _has_any_0612(raw, _STRONG_MACRO_ALLOW_PATTERNS_0612)):
            return True
        if _has_any_0612(raw, [r'nasdaq|나스닥|earnings|실적|주가|stock']) and not _has_any_0612(raw, _CRYPTO_RELATED_PATTERNS_0612):
            return True

    return False


def _should_hard_skip_0612(story: dict) -> bool:
    raw = _story_raw_0612(story)
    low = raw.lower()

    if _should_skip_unrelated_category_0612(story):
        return True

    # 특정 URL 케이스: 피드백에서 관련없음/불필요로 지정한 기사
    url = (story.get('url','') or '').lower()
    blocked_url_tokens = [
        '/news/market/369663',
        '/news/ai/369636',
        '/news/ai/369462',
        '/news/ai/369243',
        '/news/international/369470',
        '/news/insights/369297',
    ]
    if any(x in url for x in blocked_url_tokens):
        return True

    hard_patterns = [
        # flows / whales / holder movement / exchange reserves
        r'whale|고래|대형\s*보유자|보유자\s*움직임|holder\s*movement',
        r'inflows?|outflows?|순유입|순유출|유입|유출',
        r'거래소\s*(보유량|준비금)|exchange\s*(reserve|reserves|holdings|supply)',
        r'매도\s*물량|매도\s*압력|selling\s*pressure',
        r'최근\s*24시간|24\s*hours?|24시간\s*동안',
        r'wallet\s*(move|transfer)|지갑.*(이동|옮김|전송)',

        # price chart / resistance / recovery / breakout / forecast
        r'resistance|support|recovery\s*ground|breakout|돌파|저항|지지선|회복\s*여부|압축\s*구간|변동성\s*압축',
        r'price\s*(prediction|forecast|target|analysis)|가격\s*(예측|전망|분석)|목표가',
        r'bollinger|rsi|과매도|기술적\s*분석|차트',
        r'\$?\d+(?:\.\d+)?\s*(까지|돌파|도달|목표)',
        r'\d+(?:\.\d+)?달러\s*(지지선|부근|돌파|목표)',

        # generic token unlock / unlock schedule article
        r'token\s*unlock|토큰\s*언락|언락\s*이번\s*주',

        # losses
        r'손실\s*확대|nav\s*drops?|backfires|순자산가치.*감소',
    ]

    # 월드컵/예측마켓은 가격 예측이 아니라 플랫폼/매출 기사면 허용
    if _is_worldcup_robinhood_prediction_0612(raw):
        return False

    # 월드리버티파이낸셜 UFC는 중복만 막고 첫 기사라면 허용 가능
    if _is_worldliberty_ufc_0612(raw):
        return False

    return _has_any_0612(raw, hard_patterns)


def _is_worldcup_robinhood_prediction_0612(text: str) -> bool:
    low = (text or '').lower()
    return (
        ('world cup' in low or '월드컵' in low or 'fifa' in low)
        and ('robinhood' in low or '로빈후드' in low)
        and ('prediction' in low or '예측' in low or 'betting' in low)
        and ('bernstein' in low or '번스타인' in low or 'revenue' in low or '매출' in low)
    )


def _is_worldliberty_ufc_0612(text: str) -> bool:
    low = (text or '').lower()
    return (
        ('world liberty' in low or '월드리버티' in low)
        and ('ufc' in low or 'freedom 250' in low)
        and ('usd1' in low or 'stablecoin' in low or '스테이블코인' in low)
    )


_PREV_matches_keywords_0612 = matches_keywords

def matches_keywords(story, *args, **kwargs):
    if _should_hard_skip_0612(story):
        log(f"[0612 관련없음/차단 제외] {story.get('title','')}")
        return False
    return _PREV_matches_keywords_0612(story, *args, **kwargs)


_PREV_build_canonical_topic_key_0612 = build_canonical_topic_key

def build_canonical_topic_key(story: dict) -> str:
    base = _PREV_build_canonical_topic_key_0612(story)
    raw = normalize_for_duplicate(_story_raw_0612(story))
    parts = [p.strip() for p in (base or '').split('|') if p.strip()]

    if _is_worldcup_robinhood_prediction_0612(raw):
        parts.extend([
            'evt_worldcup_robinhood_prediction_revenue',
            'entity_robinhood',
            'entity_bernstein',
            'topic_worldcup',
            'topic_prediction_market',
            'topic_revenue'
        ])

    if _is_worldliberty_ufc_0612(raw):
        parts.extend([
            'evt_worldliberty_ufc_freedom250_usd1_bonus',
            'entity_worldlibertyfinancial',
            'entity_ufc',
            'topic_stablecoin',
            'asset_usd1'
        ])

    if _has_any_0612(raw, [r'bitmine|비트마인']) and _has_any_0612(raw, [r'ethereum|ether|eth|이더리움']) and _has_any_0612(raw, [r'add|buy|purchase|매입|확보']):
        parts.extend(['entity_bitmine', 'asset_eth', 'topic_treasury', 'action_buy'])

    if _has_any_0612(raw, [r'kevin\s*warsh|케빈\s*워시|케빈워시']) and _has_any_0612(raw, [r'fed|연준|금리|rates?']):
        parts.extend(['entity_kevinwarsh', 'entity_fed', 'topic_rate'])

    if _has_any_0612(raw, [r'humanity\s*protocol|휴머니티\s*프로토콜|후머니티\s*프로토콜']) and _has_any_0612(raw, [r'hack|hacking|해킹|phishing|피싱|certik|서틱']):
        parts.extend(['entity_humanityprotocol', 'topic_hacking', 'entity_certik'])

    if _has_any_0612(raw, [r'crunchbase|크런치베이스']) and _has_any_0612(raw, [r'ai|startup|스타트업|투자']):
        parts.extend(['entity_crunchbase', 'topic_ai_investment', 'geo_us'])

    parts = _normalize_sig_parts_v3(parts) if '_normalize_sig_parts_v3' in globals() else sorted(set(parts))
    if len(parts) < 3:
        return ""
    return " | ".join(parts)


def _add_inline_tags_0612(summary: str, story: dict) -> str:
    raw = _story_raw_0612(story)
    low = raw.lower()
    s = html.unescape(summary or '').strip()

    # Specific fixed summaries
    if 'durov-musk-resist-uk-social-media-ban' in low:
        return "#영국 규제 강화로 16세 미만 소셜미디어 이용 금지 방침이 추진되자, #파벨두로프 와 #일론머스크 가 공개 반대에 나섬"

    if _is_worldcup_robinhood_prediction_0612(raw):
        return "#월드컵 예측시장 급증에 #로빈후드 수혜 기대감 확대됨\n\n#번스타인 은 FIFA 관련 레버리지와 주간 스포츠 토너먼트 영향으로 예측마켓 매출이 늘 수 있다고 전함"

    if 'bitmine-adds-135m-in-eth' in low or (_has_any_0612(raw, [r'bitmine|비트마인']) and _has_any_0612(raw, [r'135m|1억3500만|5\.7|5만7|ethereum|eth|이더리움'])):
        return "#비트마인, #이더리움 5만7000 ETH를 추가 매입하며 약 1억3500만달러 규모를 더 확보함"

    if _is_worldliberty_ufc_0612(raw):
        return "#월드리버티파이낸셜, 미국 UFC Freedom 250 보너스에 #스테이블코인 USD1을 투입함\n\n#UFC 선수 보상에 스테이블코인을 활용한 사례로 주목됨"

    if 'ready-or-not-here-kevin-warsh-comes' in low:
        return "#연준 차기 의장 후보로 거론되는 #케빈워시 에 시장 관심이 집중됨\n\n시장은 기준금리 동결과 강한 고용·물가 흐름을 함께 주목하고 있음"

    if '369194' in low or (_has_any_0612(raw, [r'humanity\s*protocol|휴머니티|후머니티']) and _has_any_0612(raw, [r'hack|해킹|phishing|피싱|certik|서틱'])):
        return "#북한 연계 해킹 의혹 속 #휴머니티프로토콜 탈취 정황이 포착됨\n\n가짜 비트코브 공지로 위장한 피싱 메일이 출발점이 됐고, 약 3600만달러 규모 H토큰이 탈취된 것으로 분석됨"

    if '369499' in low or (_has_any_0612(raw, [r'crunchbase|크런치베이스']) and _has_any_0612(raw, [r'미국|us|ai|스타트업|startup|투자'])):
        return "#미국 쏠림 심화됨\n\n#크런치베이스 집계 기준 올해 전 세계 스타트업 투자금의 약 80%, #AI 투자금의 88%가 미국으로 향한 것으로 나타남"

    if '369397' in low or (_has_any_0612(raw, [r'infinity|인피니티']) and _has_any_0612(raw, [r'iso\s*27001|정보보호|보안|inex'])):
        return "#인피니티익스체인지코리아, ISO 27001:2022 인증 획득함\n\n#암호화폐 커리 서비스 운영 전반이 국제 수준 정보보호 관리체계를 공식 인정받음"

    # Phrase-level tag additions without fully rewriting
    replacements = {
        '파벨 두로프': '#파벨두로프',
        '파벨두로프': '#파벨두로프',
        '일론 머스크': '#일론머스크',
        '일론머스크': '#일론머스크',
        '로빈후드': '#로빈후드',
        '번스타인': '#번스타인',
        '월드컵': '#월드컵',
        '비트마인': '#비트마인',
        '크런치베이스': '#크런치베이스',
        '케빈 워시': '#케빈워시',
        '케빈워시': '#케빈워시',
        '휴머니티 프로토콜': '#휴머니티프로토콜',
        '후머니티 프로토콜': '#휴머니티프로토콜',
        '메타마스크': '#메타마스크',
        '월렛': '#월렛',
        '서틱': '#서틱',
    }
    for a, b in replacements.items():
        if a in s and b not in s:
            s = s.replace(a, b)

    if '영국' in s and '#영국' not in s:
        s = s.replace('영국', '#영국', 1)
    if '연준' in s and '#연준' not in s:
        s = s.replace('연준', '#연준', 1)
    if '금리' in s and '#금리' not in s:
        s = s.replace('금리', '#금리', 1)
    if '이더리움' in s and '#이더리움' not in s:
        s = s.replace('이더리움', '#이더리움', 1)

    return s


def _extra_footer_tags_0612(story: dict, summary: str) -> list[str]:
    raw = (_story_raw_0612(story) + "\n" + (summary or '')).lower()
    tags = []
    def add(t):
        if t not in tags:
            tags.append(t)

    mappings = [
        (r'durov|파벨두로프', '#PavelDurov'),
        (r'elon|musk|일론머스크', '#ElonMusk'),
        (r'uk|영국', '#UK'),
        (r'robinhood|로빈후드', '#Robinhood'),
        (r'bernstein|번스타인', '#Bernstein'),
        (r'world\s*cup|fifa|월드컵', '#WorldCup'),
        (r'prediction\s*market|예측시장|예측마켓', '#PredictionMarket'),
        (r'bitmine|비트마인', '#Bitmine'),
        (r'ethereum|ether|이더리움', '#Ethereum'),
        (r'\beth\b|eth ', '#ETH'),
        (r'crunchbase|크런치베이스', '#Crunchbase'),
        (r'(?<![A-Za-z0-9])ai(?![A-Za-z0-9])|artificial intelligence|인공지능', '#AI'),
        (r'world\s*liberty|월드리버티', '#WorldLibertyFinancial'),
        (r'\bufc\b', '#UFC'),
        (r'stablecoin|스테이블코인', '#Stablecoin'),
        (r'kevin\s*warsh|케빈워시|케빈\s*워시', '#KevinWarsh'),
        (r'fed|연준', '#Fed'),
        (r'금리|rates?', '#Rates'),
        (r'humanity\s*protocol|휴머니티프로토콜|후머니티프로토콜', '#HumanityProtocol'),
        (r'hack|hacking|해킹', '#Hacking'),
        (r'north\s*korea|dprk|북한', '#DPRK'),
        (r'certik|서틱', '#CertiK'),
        (r'wallet|지갑|월렛', '#Wallet'),
        (r'security|보안', '#Security'),
        (r'infinity|인피니티', '#InfinityExchange'),
        (r'custody|커스터디|수탁', '#Custody'),
        (r'iso\s*27001', '#ISO27001'),
    ]
    for pat, tag in mappings:
        if re.search(pat, raw, re.I):
            add(tag)

    return tags


def _merge_footer_tags_0612(msg: str, extra_tags: list[str]) -> str:
    if not msg:
        return msg
    parts = msg.split('\n\n')
    if not parts:
        return msg
    footer = html.unescape(parts[-1]).strip()
    existing = re.findall(r'#[A-Za-z0-9가-힣_]+', footer)
    merged = []
    for t in existing + extra_tags:
        if t and t not in merged:
            merged.append(t)
    for t in ['#BTC', '#비트코인', '#dooridoori', '#도리도리', '#doorinati', '#도리나티']:
        if t not in merged:
            merged.append(t)
    parts[-1] = ' '.join(html.escape(t) for t in merged)
    return '\n\n'.join(parts)


def _remove_standalone_dot_0612(text: str) -> str:
    if not text:
        return ''
    lines = [ln.strip() for ln in text.split('\n')]
    lines = [ln for ln in lines if ln not in {'.', 'ㆍ', '·'}]
    return '\n'.join(lines).strip()


_PREV_build_message_0612 = build_message

def build_message(story: dict) -> str:
    if _should_hard_skip_0612(story):
        log(f"[0612 전송전 차단] {story.get('title','')}")
        return ""

    msg = _PREV_build_message_0612(story)
    if not msg:
        return msg

    parts = msg.split('\n\n')
    if parts:
        summary = html.unescape(parts[0]).strip()
        summary = _add_inline_tags_0612(summary, story)
        summary = _remove_standalone_dot_0612(summary)
        summary = _final_ending_style_fix_0611(summary) if '_final_ending_style_fix_0611' in globals() else summary
        if 'fix_korean_hashtag_particles' in globals():
            summary = fix_korean_hashtag_particles(summary)
        if 'fix_split_person_tags' in globals():
            summary = fix_split_person_tags(summary)
        parts[0] = html.escape(summary)
        msg = '\n\n'.join(parts)
        msg = _merge_footer_tags_0612(msg, _extra_footer_tags_0612(story, summary))

    # 혹시 첫 문단이 점 하나만 남았으면 삭제
    msg = re.sub(r'\n\n\.\n\n', '\n\n', msg)
    return msg



# =========================
# 0612b generalized duplicate engine patch
# - not only fixed cases
# - entity/topic/action/number based cross-source duplicate detection
# =========================

def _story_all_text_0612b(story: dict) -> str:
    return f"{story.get('title','')} {story.get('desc','')} {story.get('summary','')} {story.get('url','')}"


def _norm_for_event_0612b(text: str) -> str:
    low = normalize_for_duplicate(text or '')
    low = low.replace('xrp ledger', 'xrpl')
    low = low.replace('ripple ledger', 'xrpl')
    low = low.replace('bank of america', 'boa')
    low = low.replace('jp morgan', 'jpmorgan')
    low = low.replace('j p morgan', 'jpmorgan')
    low = low.replace('standard chartered', 'standardchartered')
    low = low.replace('kookmin bank', 'kookminbank')
    low = low.replace('kb kookmin', 'kookminbank')
    low = low.replace('shinsei bank', 'shinseibank')
    low = low.replace('world liberty financial', 'worldlibertyfinancial')
    low = low.replace('stand with crypto', 'standwithcrypto')
    low = low.replace('pavel durov', 'paveldurov')
    low = low.replace('elon musk', 'elonmusk')
    low = low.replace('kevin warsh', 'kevinwarsh')
    low = low.replace('joseph lubin', 'josephlubin')
    low = low.replace('ashish birla', 'ashishbirla')
    low = low.replace('david schwartz', 'davidschwartz')
    low = low.replace('michael saylor', 'michaelsaylor')
    low = low.replace('jim cramer', 'jimcramer')
    return low


def _mark_if_0612b(text: str, key: str, patterns: list[str], out: list[str]):
    for p in patterns:
        if re.search(p, text, re.I):
            out.append(key)
            return


def _extract_general_event_markers_0612b(story: dict) -> list[str]:
    raw = _story_all_text_0612b(story)
    text = _norm_for_event_0612b(raw)
    out = []

    # geo
    geo_patterns = {
        'geo_us': [r'\bus\b|\busa\b|united states|america|미국'],
        'geo_uk': [r'\buk\b|united kingdom|britain|영국'],
        'geo_korea': [r'korea|south korea|한국|국내'],
        'geo_japan': [r'japan|일본'],
        'geo_hongkong': [r'hong kong|홍콩'],
        'geo_china': [r'china|중국'],
        'geo_russia': [r'russia|러시아'],
        'geo_eu': [r'europe|eu|유럽|룩셈부르크|luxembourg'],
    }
    for k, pats in geo_patterns.items():
        _mark_if_0612b(text, k, pats, out)

    # assets
    asset_patterns = {
        'asset_btc': [r'\bbtc\b|bitcoin|비트코인'],
        'asset_eth': [r'\beth\b|ethereum|ether|이더리움'],
        'asset_xrp': [r'\bxrp\b|ripple|리플'],
        'asset_xrpl': [r'\bxrpl\b|xrp ledger|xrpledger'],
        'asset_shib': [r'\bshib\b|shiba|시바이누'],
        'asset_ada': [r'\bada\b|cardano|카르다노'],
        'asset_usdt': [r'\busdt\b|tether|테더'],
        'asset_usdc': [r'\busdc\b'],
        'asset_rlusd': [r'rlusd|ripple usd'],
        'asset_usd1': [r'usd1'],
        'asset_bnb': [r'\bbnb\b|binancecoin|바이낸스코인'],
    }
    for k, pats in asset_patterns.items():
        _mark_if_0612b(text, k, pats, out)

    # entities: broad but useful
    entity_patterns = {
        'entity_ripple': [r'ripple|리플'],
        'entity_xrpledger': [r'xrpl|xrp ledger|xrpledger'],
        'entity_evernorth': [r'evernorth|에버노스'],
        'entity_brinc': [r'brinc|브링크'],
        'entity_dtcc': [r'dtcc'],
        'entity_sbi': [r'\bsbi\b|shinseibank|신세이|sbi\s*holdings'],
        'entity_zodia': [r'zodia|조디아'],
        'entity_standardchartered': [r'standardchartered|스탠다드차타드'],
        'entity_boa': [r'\bboa\b|bankofamerica|뱅크오브아메리카|뱅크 오브 아메리카'],
        'entity_jpmorgan': [r'jpmorgan|jp모건|제이피모건'],
        'entity_swift': [r'swift|스위프트'],
        'entity_cashpro': [r'cashpro|캐시프로'],
        'entity_coinbase': [r'coinbase|코인베이스'],
        'entity_chainalysis': [r'chainalysis|체이널리시스'],
        'entity_police': [r'police|경찰'],
        'entity_kookminbank': [r'kookminbank|국민은행|kb국민은행'],
        'entity_hsbc': [r'\bhsbc\b'],
        'entity_metamask': [r'metamask|메타마스크'],
        'entity_mercari': [r'mercari|메르카리'],
        'entity_robinhood': [r'robinhood|로빈후드'],
        'entity_bernstein': [r'bernstein|번스타인'],
        'entity_worldlibertyfinancial': [r'worldlibertyfinancial|월드리버티'],
        'entity_ufc': [r'\bufc\b'],
        'entity_bitmine': [r'bitmine|비트마인'],
        'entity_kevinwarsh': [r'kevinwarsh|케빈워시|케빈 워시'],
        'entity_fed': [r'\bfed\b|federal reserve|연준|fomc'],
        'entity_humanityprotocol': [r'humanity protocol|humanityprotocol|휴머니티프로토콜|후머니티프로토콜'],
        'entity_certik': [r'certik|서틱'],
        'entity_crunchbase': [r'crunchbase|크런치베이스'],
        'entity_paveldurov': [r'paveldurov|파벨두로프|파벨 두로프'],
        'entity_elonmusk': [r'elonmusk|일론머스크|일론 머스크'],
        'entity_standwithcrypto': [r'standwithcrypto|스탠드위드크립토'],
        'entity_openai': [r'openai|오픈ai|오픈에이아이'],
        'entity_chatgpt': [r'chatgpt|챗gpt'],
        'entity_josephlubin': [r'josephlubin|조셉루빈|조셉 루빈'],
        'entity_fanniemae': [r'fanniemae|패니메이'],
        'entity_freddiemac': [r'freddiemac|프레디맥'],
        'entity_sec': [r'\bsec\b|증권거래위원회'],
        'entity_cftc': [r'\bcftc\b'],
        'entity_fca': [r'\bfca\b|금융행위감독청'],
    }
    for k, pats in entity_patterns.items():
        _mark_if_0612b(text, k, pats, out)

    # topics
    topic_patterns = {
        'topic_prediction_market': [r'prediction market|prediction markets|예측시장|예측마켓'],
        'topic_worldcup': [r'world cup|fifa|월드컵'],
        'topic_revenue': [r'revenue|매출|수익'],
        'topic_socialmediaban': [r'social media ban|소셜미디어.*금지|16세.*금지'],
        'topic_crypto_transfer_limit': [r'crypto transfer|이체 제한|은행.*제한|transfer limit'],
        'topic_digitalbond': [r'digital bond|디지털채권|디지털 채권'],
        'topic_stablecoin': [r'stablecoin|스테이블코인|예금토큰|deposit token'],
        'topic_tokenization': [r'tokenization|tokenisation|토큰화'],
        'topic_custody': [r'custody|커스터디|수탁'],
        'topic_lending': [r'lending|loan|대출'],
        'topic_security': [r'security|보안|verification|검증|audit|감사|iso\s*27001'],
        'topic_hacking': [r'hack|hacking|phishing|해킹|피싱|탈취'],
        'topic_ai_investment': [r'ai.*investment|ai.*투자|스타트업.*투자|startup.*investment'],
        'topic_fed_rate': [r'interest rate|rates?|금리|기준금리'],
        'topic_fed_chair': [r'fed chair|연준.*의장|의장 후보'],
        'topic_ufc_bonus': [r'freedom 250|fighter bonus|보너스|ufc'],
        'topic_treasury': [r'treasury|재무|reserve|비축|dat|digital asset treasury'],
        'topic_purchase': [r'purchase|buy|bought|acquire|매입|매수|확보'],
        'topic_partnership': [r'partner|partnership|collaboration|협력|제휴|mou'],
        'topic_launch': [r'launch|launched|rollout|출시|도입|시작|상장'],
        'topic_approval': [r'approval|approved|license|인가|승인|라이선스'],
        'topic_regulation': [r'regulation|regulatory|규제|법안|청문회|감독'],
        'topic_crime_investigation': [r'crime|criminal|범죄|수사|경찰'],
        'topic_mortgage': [r'mortgage|주택담보대출|모기지'],
        'topic_defi': [r'defi|디파이'],
        'topic_rwa': [r'\brwa\b|real world asset|실물자산'],
    }
    for k, pats in topic_patterns.items():
        _mark_if_0612b(text, k, pats, out)

    # actions
    action_patterns = {
        'action_launch': [r'launch|launched|rollout|출시|도입|시작|상장'],
        'action_partner': [r'partner|partnership|collaboration|협력|제휴|mou'],
        'action_approve': [r'approval|approved|license|인가|승인'],
        'action_buy': [r'purchase|buy|bought|acquire|매입|매수|확보'],
        'action_invest': [r'invest|funding|투자|펀딩'],
        'action_restrict': [r'ban|restrict|limit|금지|제한'],
        'action_investigate': [r'investigate|probe|수사|조사'],
        'action_warn': [r'warn|warning|경고'],
        'action_issue': [r'issue|issued|발행'],
        'action_report': [r'report|보고|분석|집계'],
        'action_expand': [r'expand|expansion|확대'],
    }
    for k, pats in action_patterns.items():
        _mark_if_0612b(text, k, pats, out)

    # dates / amounts / numbers: useful for duplicate but not alone
    for y in re.findall(r'\b20\d{2}\b', text):
        out.append(f'year_{y}')
    for amt in re.findall(r'(\d+(?:\.\d+)?)\s*(?:million|billion|만|억|조|달러|usd|eth|btc)', text):
        # 너무 많은 숫자 오염 방지를 위해 앞 5개만
        if len([x for x in out if x.startswith('num_')]) < 5:
            out.append(f'num_{amt.replace(".", "_")}')

    # known high-confidence event aliases, generated from marker combinations
    marker_set = set(out)
    def has(*xs):
        return all(x in marker_set for x in xs)

    event_rules = [
        ('event_worldcup_robinhood_prediction_revenue', ['entity_robinhood', 'entity_bernstein', 'topic_worldcup', 'topic_prediction_market']),
        ('event_worldliberty_ufc_usd1_bonus', ['entity_worldlibertyfinancial', 'entity_ufc', 'asset_usd1']),
        ('event_kookmin_hsbc_digitalbond', ['entity_kookminbank', 'entity_hsbc', 'topic_digitalbond']),
        ('event_chainalysis_korea_police_crypto_crime', ['entity_chainalysis', 'entity_police', 'geo_korea', 'topic_crime_investigation']),
        ('event_bitmine_eth_purchase', ['entity_bitmine', 'asset_eth', 'action_buy']),
        ('event_kevinwarsh_fed_rate', ['entity_kevinwarsh', 'entity_fed', 'topic_fed_rate']),
        ('event_humanityprotocol_hacking', ['entity_humanityprotocol', 'topic_hacking']),
        ('event_crunchbase_us_ai_investment', ['entity_crunchbase', 'geo_us', 'topic_ai_investment']),
        ('event_durov_musk_uk_socialban', ['entity_paveldurov', 'entity_elonmusk', 'geo_uk', 'topic_socialmediaban']),
        ('event_standwithcrypto_uk_bank_transfer_limit', ['entity_standwithcrypto', 'geo_uk', 'topic_crypto_transfer_limit']),
        ('event_mercari_shib_listing', ['entity_mercari', 'asset_shib', 'action_launch']),
        ('event_sbi_shinsei_crypto_deposit_reward', ['entity_sbi', 'topic_stablecoin', 'action_launch']),
        ('event_zodia_luxembourg_custody_approval', ['entity_zodia', 'entity_standardchartered', 'topic_custody', 'action_approve']),
        ('event_boa_swift_xrp_payment', ['entity_boa', 'entity_swift', 'asset_xrp']),
        ('event_dtcc_xrp_tokenization', ['entity_dtcc', 'asset_xrp', 'topic_tokenization']),
    ]
    for event_key, reqs in event_rules:
        if has(*reqs):
            out.append(event_key)

    # generic event fingerprint: helps unseen future duplicate events, not just fixed cases
    ents = sorted([x for x in set(out) if x.startswith('entity_')])
    topics = sorted([x for x in set(out) if x.startswith('topic_')])
    actions = sorted([x for x in set(out) if x.startswith('action_')])
    assets = sorted([x for x in set(out) if x.startswith('asset_')])
    geos = sorted([x for x in set(out) if x.startswith('geo_')])
    nums = sorted([x for x in set(out) if x.startswith('year_') or x.startswith('num_')])

    # prevent broad false positives: require meaningful combinations
    if len(ents) >= 2 and (len(topics) >= 1 or len(actions) >= 1):
        fp_parts = ents[:4] + topics[:3] + actions[:2] + assets[:2] + geos[:1] + nums[:2]
        out.append('eventfp_' + '_'.join(fp_parts))

    elif len(ents) >= 1 and len(topics) >= 2 and (len(actions) >= 1 or len(nums) >= 1 or len(assets) >= 1):
        fp_parts = ents[:3] + topics[:4] + actions[:2] + assets[:2] + geos[:1] + nums[:2]
        out.append('eventfp_' + '_'.join(fp_parts))

    return sorted(set(out))


_PREV_build_story_signature_0612b = build_story_signature
_PREV_build_canonical_topic_key_0612b = build_canonical_topic_key

def build_story_signature(story: dict) -> str:
    base = _PREV_build_story_signature_0612b(story)
    parts = [p.strip() for p in (base or '').split('|') if p.strip()]
    parts.extend(_extract_general_event_markers_0612b(story))
    parts = _normalize_sig_parts_v3(parts) if '_normalize_sig_parts_v3' in globals() else sorted(set(parts))
    if len(parts) < 3:
        return ''
    return ' | '.join(parts)


def build_canonical_topic_key(story: dict) -> str:
    base = _PREV_build_canonical_topic_key_0612b(story)
    parts = [p.strip() for p in (base or '').split('|') if p.strip()]
    parts.extend(_extract_general_event_markers_0612b(story))
    parts = _normalize_sig_parts_v3(parts) if '_normalize_sig_parts_v3' in globals() else sorted(set(parts))
    if len(parts) < 3:
        return ''
    return ' | '.join(parts)


def _split_key_tokens_0612b(key: str) -> set[str]:
    return {x.strip() for x in (key or '').split('|') if x.strip()}


def _tokens_by_prefix_0612b(tokens: set[str], prefix: str) -> set[str]:
    return {t for t in tokens if t.startswith(prefix)}


def _duplicate_by_event_tokens_0612b(cur_key: str, old_key: str) -> bool:
    cur = _split_key_tokens_0612b(cur_key)
    old = _split_key_tokens_0612b(old_key)
    if not cur or not old:
        return False

    shared = cur & old
    shared_events = {t for t in shared if t.startswith('event_') or t.startswith('eventfp_')}
    if shared_events:
        log(f"[일반이벤트중복 제외] shared_events={shared_events}")
        return True

    cur_ent = _tokens_by_prefix_0612b(cur, 'entity_')
    old_ent = _tokens_by_prefix_0612b(old, 'entity_')
    cur_topic = _tokens_by_prefix_0612b(cur, 'topic_')
    old_topic = _tokens_by_prefix_0612b(old, 'topic_')
    cur_action = _tokens_by_prefix_0612b(cur, 'action_')
    old_action = _tokens_by_prefix_0612b(old, 'action_')
    cur_asset = _tokens_by_prefix_0612b(cur, 'asset_')
    old_asset = _tokens_by_prefix_0612b(old, 'asset_')
    cur_geo = _tokens_by_prefix_0612b(cur, 'geo_')
    old_geo = _tokens_by_prefix_0612b(old, 'geo_')
    cur_num = {t for t in cur if t.startswith('year_') or t.startswith('num_')}
    old_num = {t for t in old if t.startswith('year_') or t.startswith('num_')}

    shared_ent = cur_ent & old_ent
    shared_topic = cur_topic & old_topic
    shared_action = cur_action & old_action
    shared_asset = cur_asset & old_asset
    shared_geo = cur_geo & old_geo
    shared_num = cur_num & old_num

    # Strong duplicate: same multiple entities and at least one event topic/action.
    if len(shared_ent) >= 2 and (len(shared_topic) >= 1 or len(shared_action) >= 1):
        log(f"[일반중복 제외] shared_ent={shared_ent}, shared_topic={shared_topic}, shared_action={shared_action}")
        return True

    # Same key actor + multiple same subjects, with supporting action/asset/geo/year.
    if len(shared_ent) >= 1 and len(shared_topic) >= 2 and (shared_action or shared_asset or shared_geo or shared_num):
        log(f"[일반유사중복 제외] ent={shared_ent}, topic={shared_topic}, action={shared_action}, asset={shared_asset}, geo={shared_geo}, num={shared_num}")
        return True

    # Same entity + same action + same topic + same asset/geo/year.
    if len(shared_ent) >= 1 and len(shared_action) >= 1 and len(shared_topic) >= 1 and (shared_asset or shared_geo or shared_num):
        log(f"[액션유사중복 제외] ent={shared_ent}, topic={shared_topic}, action={shared_action}")
        return True

    return False


_PREV_is_canonical_duplicate_0612b = is_canonical_duplicate

def is_canonical_duplicate(canonical_key: str, seen_keys: set[str]) -> bool:
    if not canonical_key:
        return False

    for old_key in seen_keys:
        if _duplicate_by_event_tokens_0612b(canonical_key, old_key):
            return True

    return _PREV_is_canonical_duplicate_0612b(canonical_key, seen_keys)


def _title_token_set_0612b(title: str) -> set[str]:
    t = _norm_for_event_0612b(title)
    words = set(re.findall(r'[a-z0-9가-힣]+', t))
    noise = {
        'the', 'a', 'an', 'to', 'of', 'in', 'on', 'for', 'with', 'and', 'as', 'by',
        'says', 'said', 'new', 'could', 'may', 'will', 'why', 'how', 'what', 'here',
        '뉴스', '관련', '추진', '전망', '공개', '발표'
    }
    return {w for w in words if len(w) >= 2 and w not in noise}


_PREV_is_semantically_duplicate_0612b = is_semantically_duplicate

def is_semantically_duplicate(story: dict, seen_signatures: list[str], seen_titles: list[str]) -> bool:
    if _PREV_is_semantically_duplicate_0612b(story, seen_signatures, seen_titles):
        return True

    cur_sig = build_story_signature(story)

    for old_sig in seen_signatures:
        if _duplicate_by_event_tokens_0612b(cur_sig, old_sig):
            return True

    cur_title_norm = normalize_for_duplicate(story.get('title', ''))
    cur_words = _title_token_set_0612b(story.get('title', '') + ' ' + story.get('desc', ''))
    for old_title in seen_titles:
        old_words = _title_token_set_0612b(old_title)
        if not cur_words or not old_words:
            continue

        inter = cur_words & old_words
        union = cur_words | old_words
        jaccard = len(inter) / max(1, len(union))
        ratio = SequenceMatcher(None, cur_title_norm, old_title).ratio()

        # Title can differ by outlet wording; catch high overlap.
        if ratio >= 0.86 and len(inter) >= 4:
            log(f"[제목의미중복 제외] ratio={ratio:.2f}, shared_words={inter}")
            return True

        # Less exact title but many shared meaningful words.
        if jaccard >= 0.58 and len(inter) >= 5:
            log(f"[제목토큰중복 제외] jaccard={jaccard:.2f}, shared_words={inter}")
            return True

    return False



# =========================
# 0613 duplicate balance patch
# - fix over-aggressive previous duplicate fallback
# - do NOT treat generic tokens like action_buy/topic_purchase/action_restrict as duplicates
# - duplicate only when exact URL/title OR high-confidence event/entity-topic overlap exists
# =========================

_GENERIC_DUP_TOKENS_0613 = {
    # generic action
    'action_approve', 'action_restrict', 'action_launch', 'action_buy', 'action_invest',
    'action_partner', 'action_report', 'action_issue', 'action_통과', 'action_출시',
    'action_매수', 'action_준비', 'action_강조', 'action_발언', 'action_지지',
    'act_approval', 'act_regulation', 'act_bill', 'act_law', 'act_payment',
    'act_buy', 'act_sale', 'act_support', 'act_policy', 'act_comment',

    # generic topic
    'topic_regulation', 'topic_approval', 'topic_launch', 'topic_purchase',
    'topic_treasury', 'topic_partnership', 'topic_법안', 'topic_규제',
    'topic_라이선스', 'topic_스테이블코인', 'topic_비트코인',
    'topic_이더리움', 'topic_리플', 'topic_etf',

    # generic geo / asset
    'geo_us', 'geo_미국', 'geo_eu', 'geo_유럽', 'geo_korea', 'geo_한국',
    'geo_japan', 'geo_일본', 'asset_btc', 'asset_eth', 'asset_xrp',
    'asset_xrpl', 'asset_shib', 'asset_usdt', 'asset_usdc',
}

_BAD_OLD_EVT_TOKENS_0613 = {
    # old patches sometimes made these too broad
    'evt_mica_review',
    'evt_cme_xrp',
    'evt_rlusd',
}

def _dup_tokens_0613(key: str) -> set[str]:
    return {x.strip() for x in (key or '').split('|') if x and x.strip()}

def _specific_tokens_0613(tokens: set[str]) -> set[str]:
    return {
        t for t in tokens
        if t not in _GENERIC_DUP_TOKENS_0613
        and t not in _BAD_OLD_EVT_TOKENS_0613
        and not t.startswith('num_')
        and not t.startswith('year_')
    }

def _event_tokens_0613(tokens: set[str]) -> set[str]:
    # Trust only the newer event engine keys.
    # Old evt_* keys are too broad in this bot history, so do not use them alone.
    return {
        t for t in tokens
        if (t.startswith('event_') or t.startswith('eventfp_'))
        and t not in _BAD_OLD_EVT_TOKENS_0613
    }

def _prefix_tokens_0613(tokens: set[str], prefix: str) -> set[str]:
    return {t for t in tokens if t.startswith(prefix)}

def _title_words_0613(text: str) -> set[str]:
    try:
        norm = _norm_for_event_0612b(text)
    except Exception:
        norm = normalize_for_duplicate(text or '')
    words = set(re.findall(r'[a-z0-9가-힣]+', norm))
    noise = {
        'the','a','an','to','of','in','on','for','with','and','as','by','from',
        'says','said','new','could','may','will','why','how','what','here','reveals',
        'news','crypto','bitcoin','btc','ethereum','eth','xrp',
        '뉴스','관련','추진','전망','공개','발표','기사','암호화폐','비트코인','이더리움'
    }
    return {w for w in words if len(w) >= 2 and w not in noise}

def _is_duplicate_key_0613(cur_key: str, old_key: str) -> bool:
    cur = _dup_tokens_0613(cur_key)
    old = _dup_tokens_0613(old_key)
    if not cur or not old:
        return False

    shared_event = _event_tokens_0613(cur) & _event_tokens_0613(old)
    if shared_event:
        log(f"[0613 이벤트중복 제외] shared_event={shared_event}")
        return True

    cur_specific = _specific_tokens_0613(cur)
    old_specific = _specific_tokens_0613(old)
    shared_specific = cur_specific & old_specific

    cur_ent = _prefix_tokens_0613(cur, 'entity_') | _prefix_tokens_0613(cur, 'org_') | _prefix_tokens_0613(cur, 'person_') | _prefix_tokens_0613(cur, 'ent_')
    old_ent = _prefix_tokens_0613(old, 'entity_') | _prefix_tokens_0613(old, 'org_') | _prefix_tokens_0613(old, 'person_') | _prefix_tokens_0613(old, 'ent_')
    shared_ent = (cur_ent & old_ent) - _GENERIC_DUP_TOKENS_0613

    cur_topic = _prefix_tokens_0613(cur, 'topic_') | {t for t in cur if t.startswith('obj_') or t.startswith('bill_')}
    old_topic = _prefix_tokens_0613(old, 'topic_') | {t for t in old if t.startswith('obj_') or t.startswith('bill_')}
    shared_topic = (cur_topic & old_topic) - _GENERIC_DUP_TOKENS_0613

    cur_action = _prefix_tokens_0613(cur, 'action_') | _prefix_tokens_0613(cur, 'act_')
    old_action = _prefix_tokens_0613(old, 'action_') | _prefix_tokens_0613(old, 'act_')
    shared_action = (cur_action & old_action) - _GENERIC_DUP_TOKENS_0613

    cur_asset = _prefix_tokens_0613(cur, 'asset_')
    old_asset = _prefix_tokens_0613(old, 'asset_')
    shared_asset = (cur_asset & old_asset) - _GENERIC_DUP_TOKENS_0613

    cur_geo = _prefix_tokens_0613(cur, 'geo_')
    old_geo = _prefix_tokens_0613(old, 'geo_')
    shared_geo = (cur_geo & old_geo) - _GENERIC_DUP_TOKENS_0613

    # Strong: same multiple named entities plus a specific topic/action.
    if len(shared_ent) >= 2 and (shared_topic or shared_action or shared_asset):
        log(f"[0613 엔티티중복 제외] ent={shared_ent}, topic={shared_topic}, action={shared_action}, asset={shared_asset}")
        return True

    # Same named entity + two specific shared contexts.
    support_count = len(shared_topic) + len(shared_action) + len(shared_asset) + len(shared_geo)
    if len(shared_ent) >= 1 and support_count >= 3 and len(shared_specific) >= 4:
        log(f"[0613 의미중복 제외] ent={shared_ent}, shared_specific={shared_specific}")
        return True

    # Do not block on generic "buy/purchase/approval/regulation" alone.
    return False

def is_canonical_duplicate(canonical_key: str, seen_keys: set[str]) -> bool:
    if not canonical_key:
        return False
    for old_key in seen_keys:
        if _is_duplicate_key_0613(canonical_key, old_key):
            return True
    return False

def is_semantically_duplicate(story: dict, seen_signatures: list[str], seen_titles: list[str]) -> bool:
    title_raw = story.get('title', '') or ''
    desc_raw = story.get('desc', '') or ''
    title_norm = normalize_for_duplicate(title_raw)
    cur_sig = build_story_signature(story)

    # Title duplicate remains, but threshold is strict.
    cur_words = _title_words_0613(title_raw + ' ' + desc_raw)
    for old_title in seen_titles:
        old_words = _title_words_0613(old_title)
        ratio = SequenceMatcher(None, title_norm, old_title).ratio()
        if ratio >= 0.94:
            log(f"[0613 제목유사도 중복] ratio={ratio:.2f}")
            return True
        if cur_words and old_words:
            inter = cur_words & old_words
            union = cur_words | old_words
            jaccard = len(inter) / max(1, len(union))
            if jaccard >= 0.74 and len(inter) >= 6:
                log(f"[0613 제목토큰중복] jaccard={jaccard:.2f}, shared_words={inter}")
                return True

    for old_sig in seen_signatures:
        if _is_duplicate_key_0613(cur_sig, old_sig):
            return True

    return False



# =========================
# 0613 roundup / daily update article block patch
# - "latest update", "today's major news", "news roundup", "핵심만 정리"류 차단
# =========================

def _story_raw_0613_roundup(story: dict) -> str:
    return f"{story.get('title','')}\n{story.get('desc','')}\n{story.get('summary','')}\n{story.get('url','')}"


def _is_roundup_or_digest_article_0613(story: dict) -> bool:
    raw = _story_raw_0613_roundup(story)
    low = raw.lower()

    roundup_patterns = [
        # English roundup/digest phrases
        r'\bnews\s*roundup\b',
        r'\bdaily\s*(roundup|digest|recap|update)\b',
        r'\bweekly\s*(roundup|digest|recap|update)\b',
        r'\btoday[’\'`s]*\s*(crypto|xrp|bitcoin|market)?\s*(news|updates?|recap|digest|roundup)\b',
        r'\bwhat\s*happened\s*in\s*crypto\s*today\b',
        r'\blatest\s*(crypto|xrp|bitcoin|ripple)?\s*(news|updates?)\b',
        r'\btop\s*(crypto|xrp|bitcoin|ripple)?\s*(news|stories|headlines|updates?)\b',
        r'\beverything\s*you\s*need\s*to\s*know\b',
        r'\bkey\s*(updates?|takeaways?|headlines)\b',
        r'\bcatch\s*up\b',
        r'\bin\s*brief\b',
        r'\bbriefing\b',
        r'\bmarket\s*watch\b',
        r'\bweekend\s*watch\b',
        r'\bmorning\s*brief\b',
        r'\bevening\s*brief\b',

        # Korean roundup/digest phrases
        r'오늘\s*(주요|핵심|최신)\s*(소식|뉴스|업데이트)',
        r'금일\s*(주요|핵심|최신)\s*(소식|뉴스|업데이트)',
        r'주요\s*(소식|뉴스|업데이트)\s*(정리|요약)',
        r'최신\s*(소식|뉴스|업데이트)\s*(정리|요약)',
        r'핵심만\s*(정리|요약)',
        r'한눈에\s*(정리|보는)',
        r'한\s*눈에\s*(정리|보는)',
        r'요약\s*정리',
        r'뉴스\s*브리핑',
        r'시세\s*브리핑',
        r'시장\s*브리핑',
        r'뉴스\s*요약',
        r'종합\s*뉴스',
        r'주간\s*(정리|요약|브리핑)',
        r'일일\s*(정리|요약|브리핑)',
        r'리플\s*xrp\s*최신\s*업데이트',
        r'xrp\s*최신\s*업데이트',
        r'리플\s*최신\s*업데이트',
        r'오늘\s*주요\s*소식',
    ]

    if any(re.search(p, low, re.I) for p in roundup_patterns):
        return True

    # 크립토포테이토/유투데이/더뉴스크립토 등에서 제목이 한 종목 최신 정리형인 경우 차단
    title = (story.get('title', '') or '').lower()
    title_roundup_patterns = [
        r'(xrp|ripple|bitcoin|btc|ethereum|eth|shiba|shib).*(latest|update|updates|news).*',
        r'(latest|update|updates|news).*(xrp|ripple|bitcoin|btc|ethereum|eth|shiba|shib).*',
    ]
    if any(re.search(p, title, re.I) for p in title_roundup_patterns):
        # 단, 실제 단일 사건 기사에서 update 단어만 들어간 경우를 모두 막지는 않기 위해 roundup 단어가 있거나 내용이 정리형이면 차단
        if any(x in low for x in ['roundup', 'digest', 'recap', 'key update', 'top news', '주요 소식', '핵심만', '정리', '한눈에']):
            return True

    # 본문이 "여러 소식을 한눈에"라고 설명하는 경우
    if (
        ('한눈에' in raw or '한 눈에' in raw or '정리' in raw or '요약' in raw)
        and any(x in low for x in ['latest', 'update', 'updates', 'news', 'xrp', 'ripple', '리플'])
        and any(x in raw for x in ['주요 소식', '핵심', '생태계', '돌려싼', '둘러싼'])
    ):
        return True

    return False


# matches_keywords 단계에서 1차 차단
try:
    _PREV_matches_keywords_0613_roundup = matches_keywords

    def matches_keywords(story, *args, **kwargs):
        if _is_roundup_or_digest_article_0613(story):
            log(f"[정리/브리핑 기사 제외] {story.get('title','')}")
            return False
        return _PREV_matches_keywords_0613_roundup(story, *args, **kwargs)
except Exception:
    pass


# 전송 직전 2차 차단
try:
    _PREV_build_message_0613_roundup = build_message

    def build_message(story: dict) -> str:
        if _is_roundup_or_digest_article_0613(story):
            log(f"[전송전 정리/브리핑 기사 제외] {story.get('title','')}")
            return ""
        return _PREV_build_message_0613_roundup(story)
except Exception:
    pass


def _feed_unpack_final(feed):
    if len(feed) == 2:
        return feed[0], feed[1], False
    return feed[0], feed[1], bool(feed[2])

def _register_story_state_final(story: dict, posted: dict):
    signature = build_story_signature(story)
    canonical_key = build_canonical_topic_key(story)
    update_posted(
        story.get('title', ''),
        posted,
        story.get('url', ''),
        signature,
        canonical_key
    )

def main():
    log("Bot starting...")
    log("RUNNING_BUILD=0620_general_duplicate_engine")
    state = load_state(STATE_FILE)
    posted = state.get('posted', {})

    before_cnt = len(posted)
    posted = prune_posted_older_than(posted, days=30)
    after_cnt = len(posted)
    state['posted'] = posted
    save_state(STATE_FILE, state)
    log(f"[state 정리] 30일 초과 삭제: {before_cnt - after_cnt}개 / 유지: {after_cnt}개")

    collected = []

    for feed in FEEDS:
        name, feed_url, warmup_only = _feed_unpack_final(feed)
        stories = fetch_rss(feed_url, max_items=MAX_ITEMS_PER_FEED)
        if warmup_only:
            saved = 0
            for s in stories:
                if is_duplicate(s.get('title', ''), posted, s.get('url', '')):
                    continue
                _register_story_state_final(s, posted)
                saved += 1
            state['posted'] = posted
            save_state(STATE_FILE, state)
            log(f"{name}: {len(stories)}개 수집 / warmup_only / {saved}개 state 저장, 발송 없음")
            continue

        log(f"{name}: {len(stories)}개 수집")
        collected.extend(stories)

    filtered = [s for s in collected if matches_keywords(s, PORTFOLIO_COINS, ECON_KEYWORDS, KOREAN_KEYWORDS)]
    log(f"전체 수집 {len(collected)}개 / 필터 통과 {len(filtered)}개")

    new_stories = []
    seen_titles = [
        normalize_for_duplicate(item.get('title', ''))
        for item in posted.values()
        if item.get('title')
    ]
    seen_signatures = [
        item.get('signature', '')
        for item in posted.values()
        if item.get('signature')
    ]
    seen_urls = {
        item.get('url', '').strip()
        for item in posted.values()
        if item.get('url')
    }
    seen_topic_keys = {
        item.get('signature', '')
        for item in posted.values()
        if item.get('signature')
    }
    seen_canonical_keys = {
        item.get('canonical_key', '')
        for item in posted.values()
        if item.get('canonical_key')
    }

    for s in filtered:
        title = s.get('title', '')
        norm_title = normalize_for_duplicate(title)
        signature = build_story_signature(s)
        canonical_key = build_canonical_topic_key(s)
        url = s.get('url', '').strip()

        if signature and len(signature.split('|')) >= 3 and signature in seen_topic_keys:
            log(f"[토픽중복 제외] {title}")
            log(f"  └ 시그니처: {signature}")
            continue

        if is_canonical_duplicate(canonical_key, seen_canonical_keys):
            log(f"[정규토픽중복 제외] {title}")
            log(f"  └ canonical_key: {canonical_key}")
            continue

        if url and url in seen_urls:
            log(f"[URL중복 제외] {title}")
            continue

        if is_duplicate(title, posted, url):
            log(f"[제목/URL중복 제외] {title}")
            continue

        if is_semantically_duplicate(s, seen_signatures, seen_titles):
            log(f"[의미중복 제외] {title}")
            log(f"  └ 정규화제목: {norm_title}")
            log(f"  └ 시그니처: {signature}")
            continue

        log(f"[통과] {title}")
        log(f"  └ 정규화제목: {norm_title}")
        log(f"  └ 시그니처: {signature}")
        log(f"  └ canonical_key: {canonical_key}")

        new_stories.append(s)
        seen_titles.append(norm_title)
        seen_signatures.append(signature)
        if signature and len(signature.split('|')) >= 3:
            seen_topic_keys.add(signature)
        if canonical_key:
            seen_canonical_keys.add(canonical_key)
        if url:
            seen_urls.add(url)

    log(f"중복 제거 후 {len(new_stories)}개")
    state['posted'] = posted
    save_state(STATE_FILE, state)

    if INITIAL_RUN:
        log("INITIAL_RUN=true 상태라 텔레그램 발송 없이 종료")
        return

    if not POST_ENABLED:
        log("POST_ENABLED=false 상태라 텔레그램 발송 없이 종료")
        log(f"발송 차단된 후보: {len(new_stories)}개")

        if DRY_RUN_RECORD:
            log("DRY_RUN_RECORD=true 상태라 발송 없이 news_state.json에 기록만 진행")
            for story in new_stories:
                signature = build_story_signature(story)
                canonical_key = build_canonical_topic_key(story)
                update_posted(
                    story.get('title', ''),
                    posted,
                    story.get('url', ''),
                    signature,
                    canonical_key
                )
            state['posted'] = posted
            save_state(STATE_FILE, state)
            log(f"발송 없이 기록 완료: {len(new_stories)}개")
        else:
            log("DRY_RUN_RECORD=false 상태라 기록도 하지 않음")

        return

    for story in new_stories:
        story['image_url'] = story.get('image_url', '') or fetch_article_meta(story.get('url', ''))[1]
        msg = build_message(story)

        if not msg or not msg.strip():
            log(f"[빈메시지 스킵] {story.get('title', '')}")
            continue

        log(f"[전송준비] title={story.get('title','')[:80]}")
        log(f"[전송준비] image_url={story.get('image_url','')}")
        ok = send_telegram_photo(
            TELEGRAM_BOT_TOKEN,
            TELEGRAM_CHANNEL_ID,
            story.get('image_url', ''),
            msg
        )

        if ok:
            signature = build_story_signature(story)
            canonical_key = build_canonical_topic_key(story)
            update_posted(
                story['title'],
                posted,
                story.get('url', ''),
                signature,
                canonical_key
            )
            state['posted'] = posted
            save_state(STATE_FILE, state)
            log(f"Posted: {story['title']}")
        else:
            log(f"Failed: {story['title']}")

        time.sleep(0.3)



# =========================
# 0614 final patch: roundup/news-today/generated-summary block
# 목적:
# - "Ripple (XRP) News Today", "오늘 주요 소식", "최신 업데이트", "핵심만 정리" 같은
#   정리형/브리핑형 기사를 필터 단계와 전송 직전 단계에서 모두 차단
# =========================

def _plain_text_0614(text: str) -> str:
    text = str(text or "")
    text = re.sub(r'<[^>]+>', ' ', text)
    text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _story_text_0614(story: dict) -> str:
    return _plain_text_0614(
        f"{story.get('title','')}\n{story.get('desc','')}\n{story.get('summary','')}\n{story.get('url','')}"
    )


def _is_roundup_or_digest_article_0614(story: dict) -> bool:
    raw = _story_text_0614(story)
    low = raw.lower()

    # 제목 자체가 News Today / Latest Update / Roundup / Digest / Recap 류인 경우
    title = _plain_text_0614(story.get("title", ""))
    title_low = title.lower()

    title_patterns = [
        r'\bnews\s*today\b',
        r'\btoday\s*(crypto|xrp|ripple|bitcoin|btc|ethereum|eth|shiba|shib)?\s*news\b',
        r'\b(crypto|xrp|ripple|bitcoin|btc|ethereum|eth|shiba|shib)\s*(\([^)]*\))?\s*news\s*today\b',
        r'\b(latest|daily|weekly)\s*(crypto|xrp|ripple|bitcoin|btc|ethereum|eth|shiba|shib)?\s*(news|update|updates|digest|roundup|recap)\b',
        r'\b(crypto|xrp|ripple|bitcoin|btc|ethereum|eth|shiba|shib)\s*(latest|daily|weekly)?\s*(news|update|updates|digest|roundup|recap)\b',
        r'\bmorning\s*crypto\s*report\b',
        r'\bweekend\s*watch\b',
        r'\bmarket\s*watch\b',
        r'\bwhat\s*happened\s*in\s*crypto\s*today\b',
        r'\bcrypto\s*today\b',
    ]
    if any(re.search(p, title_low, re.I) for p in title_patterns):
        return True

    # 원문/설명에 정리형 표현이 있는 경우
    body_patterns = [
        r'\bnews\s*roundup\b',
        r'\bdaily\s*(roundup|digest|recap|brief|briefing|update)\b',
        r'\bweekly\s*(roundup|digest|recap|brief|briefing|update)\b',
        r'\btop\s*(crypto|xrp|ripple|bitcoin|btc)?\s*(news|stories|headlines|updates?)\b',
        r'\bkey\s*(updates?|takeaways?|headlines)\b',
        r'\bin\s*brief\b',
        r'\bbriefing\b',
        r'\bcatch\s*up\b',
        r'\beverything\s*you\s*need\s*to\s*know\b',

        r'오늘\s*(주요|핵심|최신)\s*(소식|뉴스|업데이트)',
        r'금일\s*(주요|핵심|최신)\s*(소식|뉴스|업데이트)',
        r'주요\s*(소식|뉴스|업데이트)\s*(정리|요약)',
        r'최신\s*(소식|뉴스|업데이트)\s*(정리|요약)',
        r'핵심만\s*(정리|요약)',
        r'한\s*눈에\s*(정리|보는|짚는)',
        r'한눈에\s*(정리|보는|짚는)',
        r'뉴스\s*브리핑',
        r'시세\s*브리핑',
        r'시장\s*브리핑',
        r'뉴스\s*요약',
        r'종합\s*뉴스',
        r'정리한\s*기사',
        r'요약\s*정리',
        r'리플\s*xrp\s*최신\s*업데이트',
        r'xrp\s*최신\s*업데이트',
        r'리플\s*최신\s*업데이트',
    ]
    return any(re.search(p, low, re.I) for p in body_patterns)


def _is_roundup_generated_message_0614(message: str) -> bool:
    plain = _plain_text_0614(message)
    low = plain.lower()

    generated_bad_patterns = [
        r'최신\s*업데이트\s*핵심만\s*정리',
        r'핵심만\s*정리한\s*기사',
        r'정리한\s*기사임',
        r'오늘\s*주요\s*소식',
        r'주요\s*소식을\s*한눈에',
        r'주요\s*소식을\s*한\s*눈에',
        r'한눈에\s*짚는\s*내용',
        r'한\s*눈에\s*짚는\s*내용',
        r'생태계를\s*둘러싼\s*오늘\s*주요\s*소식',
        r'뉴스\s*브리핑',
        r'시세\s*브리핑',
        r'시장\s*브리핑',
        r'종합\s*뉴스',
        r'news\s*today',
        r'latest\s*update',
        r'news\s*roundup',
        r'daily\s*digest',
        r'daily\s*recap',
    ]
    return any(re.search(p, low, re.I) for p in generated_bad_patterns)


try:
    _PREV_matches_keywords_0614_roundup = matches_keywords

    def matches_keywords(story, *args, **kwargs):
        if _is_roundup_or_digest_article_0614(story):
            log(f"[정리/브리핑 기사 제외 0614] {story.get('title','')}")
            return False
        return _PREV_matches_keywords_0614_roundup(story, *args, **kwargs)
except Exception:
    pass


try:
    _PREV_build_message_0614_roundup = build_message

    def build_message(story: dict) -> str:
        if _is_roundup_or_digest_article_0614(story):
            log(f"[전송전 정리/브리핑 기사 제외 0614] {story.get('title','')}")
            return ""

        msg = _PREV_build_message_0614_roundup(story)

        if _is_roundup_generated_message_0614(msg):
            log(f"[생성요약 정리/브리핑 기사 제외 0614] {story.get('title','')}")
            return ""

        return msg
except Exception:
    pass




# =========================
# 0615 safe duplicate balance patch
# 목적:
# - 기존 shared_core 방식이 topic_partnership/action_partner/topic_purchase/action_buy 같은
#   일반 토큰만 겹쳐도 중복 처리해서 "중복 제거 후 0개"가 되는 문제 수정
# - URL/제목/완전한 eventfp 중복은 유지
# - 같은 엔티티 + 같은 자산/구체토픽 + 같은 구체액션이 있을 때만 중복 처리
# =========================

_GENERIC_DUP_TOKENS_0615 = {
    # 너무 일반적인 액션
    'action_partner', 'action_buy', 'action_launch', 'action_approve', 'action_restrict',
    'action_invest', 'action_report', 'action_expand', 'action_issue', 'action_warn',
    'action_통과', 'action_매수', 'action_출시', 'action_강조', 'action_촉구',
    'act_buy', 'act_payment', 'act_approval', 'act_bill', 'act_law',
    'act_institutional', 'act_regulation', 'act_risk', 'act_comment',

    # 너무 일반적인 토픽
    'topic_partnership', 'topic_purchase', 'topic_launch', 'topic_approval',
    'topic_regulation', 'topic_fed_rate', 'topic_treasury', 'topic_재무부',
    'topic_ai', 'topic_defi', 'topic_lending', 'topic_stablecoin',
    'topic_법안', 'topic_규제', 'topic_시장구조법안',

    # 잘못 붙는 경우가 많아서 중복 기준에서는 제외
    'topic_비트마인가',
    'evt_qivalis_banks',
    'evt_cme_xrp',
    'evt_occ_warren',
    'evt_trump_fed_master',
}


def _split_dup_tokens_0615(key: str) -> set[str]:
    return {x.strip() for x in (key or '').split('|') if x.strip()}


def _eventfp_tokens_0615(tokens: set[str]) -> set[str]:
    # eventfp는 구체 이벤트 fingerprint라서 완전 동일할 때만 중복으로 인정
    return {t for t in tokens if t.startswith('eventfp_')}


def _entity_tokens_0615(tokens: set[str]) -> set[str]:
    return {
        t for t in tokens
        if (
            t.startswith('entity_')
            or t.startswith('org_')
            or t.startswith('person_')
            or t.startswith('bill_')
            or t.startswith('obj_')
        )
        and t not in _GENERIC_DUP_TOKENS_0615
    }


def _asset_tokens_0615(tokens: set[str]) -> set[str]:
    return {t for t in tokens if t.startswith('asset_')}


def _geo_tokens_0615(tokens: set[str]) -> set[str]:
    return {t for t in tokens if t.startswith('geo_')}


def _topic_tokens_0615(tokens: set[str]) -> set[str]:
    return {
        t for t in tokens
        if t.startswith('topic_') and t not in _GENERIC_DUP_TOKENS_0615
    }


def _action_tokens_0615(tokens: set[str]) -> set[str]:
    return {
        t for t in tokens
        if (t.startswith('action_') or t.startswith('act_'))
        and t not in _GENERIC_DUP_TOKENS_0615
    }


def _title_similarity_duplicate_0615(a: str, b: str) -> bool:
    a = normalize_for_duplicate(a or '')
    b = normalize_for_duplicate(b or '')
    if not a or not b:
        return False
    if a == b:
        return True
    return SequenceMatcher(None, a, b).ratio() >= 0.92


def _should_duplicate_by_tokens_0615(cur: set[str], old: set[str]) -> tuple[bool, str]:
    cur_eventfp = _eventfp_tokens_0615(cur)
    old_eventfp = _eventfp_tokens_0615(old)
    shared_eventfp = cur_eventfp & old_eventfp
    if shared_eventfp:
        return True, f"eventfp={shared_eventfp}"

    cur_ent, old_ent = _entity_tokens_0615(cur), _entity_tokens_0615(old)
    cur_asset, old_asset = _asset_tokens_0615(cur), _asset_tokens_0615(old)
    cur_topic, old_topic = _topic_tokens_0615(cur), _topic_tokens_0615(old)
    cur_action, old_action = _action_tokens_0615(cur), _action_tokens_0615(old)
    cur_geo, old_geo = _geo_tokens_0615(cur), _geo_tokens_0615(old)

    shared_ent = cur_ent & old_ent
    shared_asset = cur_asset & old_asset
    shared_topic = cur_topic & old_topic
    shared_action = cur_action & old_action
    shared_geo = cur_geo & old_geo

    # 같은 회사/기관 + 같은 자산 + 같은 구체토픽이면 중복
    # 예: SBI + RLUSD/XRP + 일본 승인, 같은 거래소 인수 기사 등
    if shared_ent and shared_asset and shared_topic:
        return True, f"entity+asset+topic ent={shared_ent}, asset={shared_asset}, topic={shared_topic}"

    # 같은 회사/기관 + 구체토픽 2개 이상 + 구체액션이면 중복
    if shared_ent and len(shared_topic) >= 2 and shared_action:
        return True, f"entity+topics+action ent={shared_ent}, topic={shared_topic}, action={shared_action}"

    # 같은 회사/기관 + 같은 지역 + 구체토픽 + 구체액션이면 중복
    if shared_ent and shared_geo and shared_topic and shared_action:
        return True, f"entity+geo+topic+action ent={shared_ent}, geo={shared_geo}, topic={shared_topic}, action={shared_action}"

    # 같은 법안/정책 토큰 + 같은 구체토픽 + 같은 지역이면 중복
    # 단순 action_approve/topic_approval 같은 일반 토큰만으로는 여기까지 못 옴
    if shared_ent and shared_topic and shared_geo and not (shared_asset or shared_action):
        if any(t.startswith('bill_') or t.startswith('obj_') for t in shared_ent):
            return True, f"bill/object+topic+geo ent={shared_ent}, topic={shared_topic}, geo={shared_geo}"

    return False, ""


def is_canonical_duplicate(canonical_key: str, seen_keys: set[str]) -> bool:
    if not canonical_key:
        return False

    cur = _split_dup_tokens_0615(canonical_key)

    for old_key in seen_keys:
        old = _split_dup_tokens_0615(old_key)
        ok, reason = _should_duplicate_by_tokens_0615(cur, old)
        if ok:
            log(f"[정규토픽중복 제외 0615] {reason}")
            return True

    return False


def is_semantically_duplicate(story: dict, seen_signatures: list[str], seen_titles: list[str]) -> bool:
    title = story.get('title', '')
    norm_title = normalize_for_duplicate(title)

    # 제목이 거의 같은 경우는 중복 유지
    for old_title in seen_titles:
        if _title_similarity_duplicate_0615(norm_title, old_title):
            log(f"[제목유사도 중복 0615] {norm_title} <> {old_title}")
            return True

    signature = build_story_signature(story)
    cur = _split_dup_tokens_0615(signature)

    if len(cur) < 3:
        return False

    for old_sig in seen_signatures:
        old = _split_dup_tokens_0615(old_sig)
        ok, reason = _should_duplicate_by_tokens_0615(cur, old)
        if ok:
            log(f"[의미중복 제외 0615] {reason}")
            return True

    return False




# =========================
# 0616 AI footer guard patch
# 목적:
# - 기사 내용과 무관하게 footer 끝에 #AI가 붙는 문제 방지
# - Chainlink / main / raise / campaign 같은 단어 안의 ai를 AI로 오인하지 않게 방지
# - 진짜 AI 기사일 때만 #AI 유지
# =========================

def _story_raw_0616_ai_guard(story: dict) -> str:
    return f"{story.get('title','')}\n{story.get('desc','')}\n{story.get('summary','')}\n{story.get('url','')}"


def _has_real_ai_reference_0616(story: dict, summary: str = "") -> bool:
    raw = f"{_story_raw_0616_ai_guard(story)}\n{summary or ''}"

    # OpenAI / Anthropic 같은 이름 자체는 #OpenAI / #Anthropic으로 처리하면 되고,
    # 모든 기사에 #AI를 붙일 이유는 없음.
    # 다만 기사 본문에 독립 단어 AI, 인공지능, artificial intelligence가 실제로 나오면 #AI 유지.
    real_ai_patterns = [
        r'(?<![A-Za-z0-9])AI(?![A-Za-z0-9])',
        r'artificial\s+intelligence',
        r'인공지능',
        r'AI\s*(투자|산업|칩|반도체|데이터|모델|기업|스타트업|검색|에이전트|agent|model|chip|data|startup|investment|industry)',
    ]

    return any(re.search(p, raw, re.I) for p in real_ai_patterns)


def _remove_unrelated_ai_footer_0616(message: str, story: dict) -> str:
    if not message or '#AI' not in message:
        return message

    parts = message.split('\n\n')
    if len(parts) < 2:
        return message.replace('#AI', '').replace('  ', ' ').strip()

    summary_part = html.unescape(parts[0])

    if _has_real_ai_reference_0616(story, summary_part):
        return message

    # 일반 footer 태그 줄에서만 #AI 제거
    footer = parts[-1]
    footer_tags = [t for t in footer.split() if t.strip() and t.strip() != '#AI']

    parts[-1] = ' '.join(footer_tags)

    # 혹시 footer가 비면 빈 줄 정리
    out = '\n\n'.join(p for p in parts if p.strip())
    out = re.sub(r'[ \t]+', ' ', out)
    out = re.sub(r'\n{3,}', '\n\n', out).strip()

    try:
        log(f"[AI태그 제거 0616] 내용상 AI 기사 아님: {story.get('title','')}")
    except Exception:
        pass

    return out


try:
    _PREV_build_message_0616_ai_guard = build_message

    def build_message(story: dict) -> str:
        msg = _PREV_build_message_0616_ai_guard(story)
        return _remove_unrelated_ai_footer_0616(msg, story)
except Exception:
    pass




# =========================
# 0617 duplicate + unwanted article filter patch
# 목적:
# 1) 같은 이슈가 여러 매체에서 반복 업로드되는 문제 완화
# 2) 생활앱/카드전시/비포폴체인 AI전환/설문·심리/부동산 대출포트폴리오 기사 차단
# 3) #Rates #Lending #Bank 같은 의미 약한 footer 태그 제거
# =========================

def _story_text_0617(story: dict) -> str:
    return f"{story.get('title','')}\n{story.get('desc','')}\n{story.get('summary','')}\n{story.get('url','')}"


def _match_any_0617(text: str, patterns: list[str]) -> bool:
    return any(re.search(p, text or "", re.I) for p in patterns)


def _is_unwanted_article_0617(story: dict) -> tuple[bool, str]:
    raw = _story_text_0617(story)
    low = raw.lower()

    # 7번: Sleepagotchi 같은 Web3/AI 건강·수면·영양 생활앱
    if _match_any_0617(low, [
        r'sleepagotchi',
        r'health\s*coach',
        r'web3\s*health',
        r'sleep\s*data',
        r'nutrition\s*data',
        r'smartphone\s*app',
        r'건강\s*코치',
        r'헬스\s*앱',
        r'수면.*영양',
        r'수면.*데이터',
        r'영양.*데이터',
    ]):
        return True, "생활앱/웹3헬스 제외"

    # 8번: Bitcoin Asia 카드 전시/트레이딩 카드/아트 프로그램
    if _match_any_0617(low, [
        r'\bbmag\b',
        r'bitcoin\s*asia.*card',
        r'card\s*expo',
        r'trading\s*card',
        r'card\s*exhibition',
        r'카드\s*엑스포',
        r'카드\s*전시',
        r'트레이딩\s*카드',
        r'아트\s*프로그램',
        r'컨벤션전시센터.*카드',
    ]):
        return True, "카드전시/행사 제외"

    # 9번: ZetaChain 등 비포폴 체인 + AI 전환/제품 방향 재편
    if _match_any_0617(low, [
        r'zetachain',
        r'zeta\s*chain',
        r'기존\s*크로스체인\s*서비스',
        r'cross[-\s]*chain\s*service',
        r'ai\s*전환',
        r'제품\s*방향\s*재편',
        r'product\s*direction',
    ]):
        return True, "비포폴체인/AI전환 제외"

    # 10번: 월가/기관투자자 노출도·설문·심리성 기사
    if _match_any_0617(low, [
        r'wealthy\s*investors?',
        r'wealth\s*advis[oe]rs?',
        r'underexposed',
        r'exposure\s*(?:is|remains|still)',
        r'survey',
        r'설문',
        r'소극적',
        r'무기한선',
        r'여전히\s*소극',
        r'암호화폐\s*노출',
    ]):
        return True, "설문/투자심리 제외"

    # 11번: 일반 부동산·상업용 대출 포트폴리오/부실자산 기사
    has_real_estate = _match_any_0617(low, [
        r'commercial\s*real\s*estate',
        r'office\s*space',
        r'multifamily',
        r'mortgage',
        r'default',
        r'distressed\s*asset',
        r'상업용\s*부동산',
        r'오피스\s*공실',
        r'다세대\s*대출',
        r'주택담보',
        r'부실\s*자산',
        r'익스포저',
    ])
    has_loan_portfolio = _match_any_0617(low, [
        r'loan\s*portfolio',
        r'대출\s*포트폴리오',
        r'대출\s*매각',
        r'채무',
        r'재투자',
    ])
    if has_real_estate and has_loan_portfolio:
        return True, "부동산/대출포트폴리오 제외"

    return False, ""


# 기존 matches_keywords를 한 번 더 감싸서 불필요 기사 선차단
try:
    _PREV_matches_keywords_0617 = matches_keywords

    def matches_keywords(story: dict, coins: list[str], econ_keywords: list[str], korean_keywords: list[str]) -> bool:
        blocked, reason = _is_unwanted_article_0617(story)
        if blocked:
            print(f"[{reason}] {story.get('title', '')}")
            return False
        return _PREV_matches_keywords_0617(story, coins, econ_keywords, korean_keywords)
except Exception:
    pass


# 중복 이벤트 마커 추가: 같은 뉴스가 매체만 바뀌어 반복 업로드되는 경우 잡기
_EVENT_MARKER_PATTERNS_0617 = {
    'evt_xrpl_lending_protocol': [
        r'(xrp\s*ledger|xrpl|xrpledger|리플|xrp).{0,80}(lending|loan|loans|yield|yields|대출|수익)',
        r'(lending|loan|loans|yield|yields|대출|수익).{0,80}(xrp\s*ledger|xrpl|xrpledger|리플|xrp)',
    ],
    'evt_open_stablecoin_us_members': [
        r'(mastercard|blackrock|google|마스터카드|블랙록|구글).{0,120}(stablecoin|스테이블코인)',
        r'(stablecoin|스테이블코인).{0,120}(mastercard|blackrock|google|마스터카드|블랙록|구글)',
    ],
    'evt_uk_fca_crypto_rules_2027': [
        r'(fca|financial\s*conduct\s*authority|영국).{0,100}(crypto|암호화폐|stablecoin|스테이블코인|custody|수탁|lending|대출).{0,120}(2027|rules|rule|regulation|규제|공개|최종)',
        r'(2027|rules|rule|regulation|규제|공개|최종).{0,120}(fca|financial\s*conduct\s*authority|영국)',
    ],
    'evt_trump_cbdc_housing_act': [
        r'(trump|트럼프).{0,120}(cbdc|housing|21st\s*century\s*road\s*to\s*housing|주택)',
        r'(cbdc).{0,120}(trump|트럼프|housing|주택)',
    ],
    'evt_bybit_mica_eea_custody': [
        r'(bybit|바이비트).{0,120}(mica|eea|custody|수탁|마감|시한)',
        r'(mica|eea|custody|수탁|마감|시한).{0,120}(bybit|바이비트)',
    ],
}


def _extract_event_markers_0617(text: str) -> list[str]:
    raw = text or ""
    found = []
    for marker, patterns in _EVENT_MARKER_PATTERNS_0617.items():
        if _match_any_0617(raw, patterns):
            found.append(marker)
    return sorted(set(found))


def _append_event_markers_0617(base_key: str, story: dict) -> str:
    parts = [p.strip() for p in (base_key or "").split("|") if p.strip()]
    parts.extend(_extract_event_markers_0617(_story_text_0617(story)))

    # 너무 일반적인 토큰만 남은 signature가 exact-match 중복을 만들지 않도록 약화
    generic = {
        'action_partner', 'topic_partnership', 'action_buy', 'topic_purchase',
        'action_launch', 'topic_launch', 'action_approve', 'topic_approval',
        'action_restrict', 'topic_fed_rate', 'topic_treasury', 'org_sec',
        'geo_us', 'geo_eu', 'year_2026'
    }
    strong_prefixes = ('asset_', 'entity_', 'org_', 'person_', 'bill_', 'evt_')
    has_strong = any(p.startswith(strong_prefixes) for p in parts)
    has_event = any(p.startswith('evt_') for p in parts)

    if not has_event and not has_strong:
        return ""

    if not has_event:
        # 일반 토픽만으로 너무 짧은 signature면 중복키로 쓰지 않음
        non_generic = [p for p in parts if p not in generic]
        if len(non_generic) < 2 and len(parts) <= 4:
            return ""

    seen = set()
    out = []
    for p in sorted(parts):
        if p and p not in seen:
            out.append(p)
            seen.add(p)
    return " | ".join(out)


try:
    _PREV_build_story_signature_0617 = build_story_signature
    _PREV_build_canonical_topic_key_0617 = build_canonical_topic_key

    def build_story_signature(story: dict) -> str:
        return _append_event_markers_0617(_PREV_build_story_signature_0617(story), story)

    def build_canonical_topic_key(story: dict) -> str:
        return _append_event_markers_0617(_PREV_build_canonical_topic_key_0617(story), story)
except Exception:
    pass


def _tokens_0617(key: str) -> set:
    return {x.strip() for x in (key or "").split("|") if x.strip()}


def _event_tokens_0617(key: str) -> set:
    return {t for t in _tokens_0617(key) if t.startswith("evt_")}


def _specific_tokens_0617(key: str) -> set:
    generic = {
        'action_partner', 'topic_partnership', 'action_buy', 'topic_purchase',
        'action_launch', 'topic_launch', 'action_approve', 'topic_approval',
        'action_restrict', 'topic_fed_rate', 'topic_treasury',
        'geo_us', 'geo_eu', 'year_2026'
    }
    return {t for t in _tokens_0617(key) if t not in generic}


# 기존 의미중복이 넓은 shared_core 2개만으로 과차단하지 않도록 더 안전하게 교체
try:
    def is_canonical_duplicate(canonical_key: str, seen_keys: set[str]) -> bool:
        if not canonical_key:
            return False

        cur_events = _event_tokens_0617(canonical_key)
        cur_specific = _specific_tokens_0617(canonical_key)

        for old_key in seen_keys:
            old_events = _event_tokens_0617(old_key)
            shared_events = cur_events & old_events
            if shared_events:
                log(f"[이벤트중복 제외 0617] shared_event={shared_events}")
                return True

            old_specific = _specific_tokens_0617(old_key)
            shared_specific = cur_specific & old_specific

            # 이벤트 마커가 없으면 매우 강한 경우만 중복 처리
            has_same_entity = any(t.startswith(('entity_', 'org_', 'person_', 'bill_')) for t in shared_specific)
            has_same_asset = any(t.startswith('asset_') for t in shared_specific)
            has_same_topic = any(t.startswith('topic_') for t in shared_specific)
            has_same_action = any(t.startswith('action_') or t.startswith('act_') for t in shared_specific)

            if has_same_entity and has_same_asset and has_same_topic and has_same_action:
                log(f"[정규토픽중복 제외 0617] shared_specific={shared_specific}")
                return True

        return False


    def is_semantically_duplicate(story: dict, seen_signatures: list[str], seen_titles: list[str]) -> bool:
        title = normalize_for_duplicate(story.get('title', ''))
        signature = build_story_signature(story)

        for old_title in seen_titles:
            ratio = SequenceMatcher(None, title, old_title).ratio()
            if ratio >= 0.92:
                log(f"[제목유사도 중복 0617] {title} <> {old_title} / {ratio:.2f}")
                return True

        cur_events = _event_tokens_0617(signature)
        cur_specific = _specific_tokens_0617(signature)

        for old_sig in seen_signatures:
            old_events = _event_tokens_0617(old_sig)
            shared_events = cur_events & old_events
            if shared_events:
                log(f"[이벤트중복 제외 0617] shared_event={shared_events}")
                return True

            old_specific = _specific_tokens_0617(old_sig)
            shared_specific = cur_specific & old_specific

            has_same_entity = any(t.startswith(('entity_', 'org_', 'person_', 'bill_')) for t in shared_specific)
            has_same_asset = any(t.startswith('asset_') for t in shared_specific)
            has_same_topic = any(t.startswith('topic_') for t in shared_specific)
            has_same_action = any(t.startswith('action_') or t.startswith('act_') for t in shared_specific)

            if has_same_entity and has_same_asset and has_same_topic and has_same_action:
                log(f"[의미중복 제외 0617] shared_specific={shared_specific}")
                return True

        return False
except Exception:
    pass


# footer 정리: 내용이 빈약한 영어 일반 태그 제거
_BAD_FOOTER_TAGS_0617 = {
    '#AI가', '#Rates', '#Rate', '#Lending', '#Loan', '#Loans', '#Bank', '#Banks',
    '#Health', '#Sleep', '#Nutrition', '#Expo', '#Card', '#Cards'
}

try:
    _PREV_build_message_0617_footer = build_message

    def build_message(story: dict) -> str:
        msg = _PREV_build_message_0617_footer(story)
        if not msg:
            return msg

        parts = msg.split('\n\n')
        if len(parts) >= 4:
            footer = parts[-1]
            tags = []
            seen = set()
            for t in footer.split():
                tt = t.strip()
                if not tt or tt in _BAD_FOOTER_TAGS_0617:
                    continue
                if tt not in seen:
                    tags.append(tt)
                    seen.add(tt)
            parts[-1] = ' '.join(tags)
            msg = '\n\n'.join(p for p in parts if p.strip())

        return msg
except Exception:
    pass




# =========================
# 0618 inline body tag restore patch
# 목적:
# - 최신 패치에서 본문 해시태그가 너무 많이 사라진 문제 복구
# - footer는 기존처럼 유지하되, 본문 첫 문장 안에 핵심 국가/기관/회사/법안 태그를 다시 삽입
# - 최대 5개까지만 본문 태그 사용
# =========================

_INLINE_BODY_TAG_SPECS_0618 = [
    # 국가
    ('영국', [r'(?<![A-Za-z0-9])uk(?![A-Za-z0-9])', r'united\s+kingdom', r'britain', r'영국']),
    ('미국', [r'(?<![A-Za-z0-9])u\.?s\.?(?![A-Za-z0-9])', r'(?<![A-Za-z0-9])usa(?![A-Za-z0-9])', r'united\s+states', r'미국']),
    ('러시아', [r'(?<![A-Za-z0-9])russia(?![A-Za-z0-9])', r'러시아']),
    ('필리핀', [r'philippines', r'필리핀']),
    ('홍콩', [r'hong\s+kong', r'홍콩']),
    ('일본', [r'(?<![A-Za-z0-9])japan(?![A-Za-z0-9])', r'일본']),
    ('한국', [r'south\s+korea', r'(?<![A-Za-z0-9])korea(?![A-Za-z0-9])', r'한국']),

    # 규제기관/공공기관
    ('SEC', [r'(?<![A-Za-z0-9])sec(?![A-Za-z0-9])', r'증권거래위원회', r'증권\s*위원회']),
    ('FCA', [r'(?<![A-Za-z0-9])fca(?![A-Za-z0-9])', r'financial\s+conduct\s+authority']),
    ('CFTC', [r'(?<![A-Za-z0-9])cftc(?![A-Za-z0-9])']),
    ('연준', [r'federal\s+reserve', r'(?<![A-Za-z0-9])fed(?![A-Za-z0-9])', r'연준']),
    ('중앙은행', [r'central\s+bank', r'중앙은행']),
    ('홍콩금융관리국', [r'(?<![A-Za-z0-9])hkma(?![A-Za-z0-9])', r'hong\s+kong\s+monetary\s+authority', r'홍콩금융관리국']),

    # 회사/기관
    ('마이크로소프트', [r'microsoft', r'마이크로소프트']),
    ('바이낸스', [r'binance', r'바이낸스']),
    ('바이비트', [r'bybit', r'바이비트']),
    ('구글', [r'google', r'구글']),
    ('블랙록', [r'blackrock', r'블랙록']),
    ('마스터카드', [r'mastercard', r'마스터카드']),
    ('JPMorgan', [r'j\.?p\.?\s*morgan', r'jpmorgan', r'jp모건', r'제이피모건']),
    ('Ripple', [r'(?<![A-Za-z0-9])ripple(?![A-Za-z0-9])', r'리플']),
    ('XRPLedger', [r'xrp\s*ledger', r'xrpl', r'xrpledger']),

    # 주요 주제/법안/자산
    ('XRP', [r'(?<![A-Za-z0-9])xrp(?![A-Za-z0-9])']),
    ('CBDC', [r'(?<![A-Za-z0-9])cbdc(?![A-Za-z0-9])']),
    ('MiCA', [r'(?<![A-Za-z0-9])mica(?![A-Za-z0-9])', r'미카']),
    ('EEA', [r'(?<![A-Za-z0-9])eea(?![A-Za-z0-9])']),
    ('스테이블코인', [r'stablecoin', r'stablecoins', r'스테이블코인']),
    ('디지털루블', [r'digital\s+ruble', r'digital\s+rouble', r'디지털\s*루블']),
    ('AI', [r'(?<![A-Za-z0-9])ai(?![A-Za-z0-9])', r'artificial\s+intelligence', r'인공지능']),
    ('수탁', [r'custody', r'custodial', r'수탁']),
    ('대출', [r'lending', r'loan', r'loans', r'대출']),
    ('은행', [r'bank', r'banks', r'은행']),
]

# 본문에 실제로 쓰이는 표기 후보
_INLINE_BODY_SURFACE_0618 = {
    '영국': ['영국', 'UK', 'United Kingdom'],
    '미국': ['미국', 'US', 'U.S.', 'United States'],
    '러시아': ['러시아', 'Russia'],
    '필리핀': ['필리핀', 'Philippines'],
    '홍콩': ['홍콩', 'Hong Kong'],
    '일본': ['일본', 'Japan'],
    '한국': ['한국', 'South Korea', 'Korea'],
    'SEC': ['SEC'],
    'FCA': ['FCA'],
    'CFTC': ['CFTC'],
    '연준': ['연준', 'Fed', 'Federal Reserve'],
    '중앙은행': ['중앙은행', 'Central Bank'],
    '홍콩금융관리국': ['홍콩금융관리국', 'HKMA'],
    '마이크로소프트': ['마이크로소프트', 'Microsoft'],
    '바이낸스': ['바이낸스', 'Binance'],
    '바이비트': ['바이비트', 'Bybit'],
    '구글': ['구글', 'Google'],
    '블랙록': ['블랙록', 'BlackRock'],
    '마스터카드': ['마스터카드', 'Mastercard'],
    'JPMorgan': ['JPMorgan', 'JP모건', '제이피모건'],
    'Ripple': ['리플', 'Ripple'],
    'XRPLedger': ['XRPLedger', 'XRP Ledger', 'XRPL'],
    'XRP': ['XRP'],
    'CBDC': ['CBDC'],
    'MiCA': ['MiCA', '미카'],
    'EEA': ['EEA'],
    '스테이블코인': ['스테이블코인', 'stablecoin', 'stablecoins'],
    '디지털루블': ['디지털 루블', '디지털루블', 'digital ruble'],
    'AI': ['AI', '인공지능'],
    '수탁': ['수탁', 'custody'],
    '대출': ['대출', 'lending', 'loan'],
    '은행': ['은행', 'bank'],
}

_INLINE_BODY_GENERIC_0618 = {'은행', '대출', '수탁', 'AI', '스테이블코인'}


def _has_inline_term_0618(text: str, patterns: list[str]) -> bool:
    return any(re.search(p, text or '', re.I) for p in patterns)


def _select_inline_body_labels_0618(summary: str, story: dict, max_tags: int = 5) -> list[str]:
    raw = f"{story.get('title','')}\n{story.get('desc','')}\n{story.get('url','')}"
    base = f"{summary or ''}\n{raw}"

    selected = []
    for label, patterns in _INLINE_BODY_TAG_SPECS_0618:
        if label in selected:
            continue
        if _has_inline_term_0618(base, patterns):
            # AI는 진짜 AI 기사일 때만
            if label == 'AI':
                try:
                    if not _has_real_ai_reference_0616(story, summary):
                        continue
                except Exception:
                    pass
            selected.append(label)
        if len(selected) >= max_tags:
            break

    # 일반 주제 태그만 너무 많이 잡히지 않게 뒤에서 정리
    strong = [x for x in selected if x not in _INLINE_BODY_GENERIC_0618]
    generic = [x for x in selected if x in _INLINE_BODY_GENERIC_0618]

    if len(strong) >= 3:
        selected = strong[:max_tags]
    else:
        selected = (strong + generic)[:max_tags]

    return selected


def _replace_first_surface_with_tag_0618(text: str, label: str) -> tuple[str, bool]:
    if f'#{label}' in text:
        return text, True

    surfaces = _INLINE_BODY_SURFACE_0618.get(label, [label])

    for surface in sorted(surfaces, key=len, reverse=True):
        if not surface:
            continue

        # 영어/숫자 표기는 단어 경계, 한글은 단순 첫 등장
        if re.search(r'[A-Za-z0-9]', surface):
            pat = rf'(?<![#A-Za-z0-9]){re.escape(surface)}(?![A-Za-z0-9])'
        else:
            pat = rf'(?<!#){re.escape(surface)}'

        new_text, count = re.subn(pat, f'#{label}', text, count=1, flags=re.I)
        if count:
            return new_text, True

    return text, False


def _restore_inline_body_tags_0618(summary: str, story: dict) -> str:
    if not summary:
        return summary

    text = html.unescape(summary)
    labels = _select_inline_body_labels_0618(text, story, max_tags=5)

    missing_prefix = []
    for label in labels:
        if f'#{label}' in text:
            continue

        text, replaced = _replace_first_surface_with_tag_0618(text, label)
        if not replaced:
            missing_prefix.append(f'#{label}')

    # 본문에 단어가 안 보이는 핵심 태그는 첫 문장 앞에 붙임
    if missing_prefix:
        first_line_split = text.split('\n', 1)
        first = first_line_split[0].strip()
        rest = first_line_split[1] if len(first_line_split) > 1 else ''
        prefix = ' '.join(missing_prefix[:5])
        if first:
            first = f'{prefix} {first}'
        else:
            first = prefix
        text = first + (('\n' + rest) if rest else '')

    text = fix_split_person_tags(text)
    text = fix_korean_hashtag_particles(text)

    # 잘못 붙은 조사/공백 정리
    text = re.sub(r'#([A-Za-z0-9가-힣_]+)\s+([,])', r'#\1\2', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    return text


try:
    _PREV_build_message_0618_inline_restore = build_message

    def build_message(story: dict) -> str:
        msg = _PREV_build_message_0618_inline_restore(story)
        if not msg:
            return msg

        parts = msg.split('\n\n')
        if len(parts) < 4:
            return msg

        summary = html.unescape(parts[0])
        summary = _restore_inline_body_tags_0618(summary, story)
        parts[0] = html.escape(summary)

        return '\n\n'.join(parts)
except Exception:
    pass




# =========================
# 0619 quality filter + duplicate + Korean body tag + ending patch
# 목적:
# - 반복 업로드되는 같은 이슈를 이벤트 단위로 중복 차단
# - 가격/급등락/지갑증감/이체/출금/회복세/재진입/압박성 기사 차단
# - 크립토와 직접 관련 없는 일반 산업/주식/행사 기사 차단
# - 영어 엔티티를 본문 한국어 해시태그로 변환
# - 했. / 했음고전함 / 했음고함 / 시장구조#법안 같은 문장 오류 보정
# =========================

try:
    MANUAL_TRANSLATIONS.update({
        'Polymarket': '폴리마켓',
        'CACEIS': '카세스',
        'Caceis': '카세스',
        'Meria': '메리아',
        'India': '인도',
        'Micron': '마이크론',
        'Micron Technology': '마이크론',
        'IMF': 'IMF',
        'Germany': '독일',
        'Cardano': '카르다노',
        'ADA': '카르다노',
        'Dubai': '두바이',
        'Alibaba': '알리바바',
        'Michael Saylor': '마이클세일러',
        'Saylor': '마이클세일러',
        'Tom Lee': '톰리',
        'Thomas Lee': '톰리',
        'BitMine': '비트마인',
        'Bitmine': '비트마인',
        'Market Structure Bill': '시장구조법안',
        'CLARITY Act': '시장구조법안',
    })

    _ADD_INLINE_0619 = {
        '폴리마켓', '카세스', '메리아', '인도', '마이크론', 'IMF', '독일',
        '카르다노', '두바이', '알리바바', '마이클세일러', '톰리',
        '비트마인', '시장구조법안', '바이비트', '업비트', '필리핀',
        '중국', '러시아', '중앙은행', '디지털루블'
    }
    INLINE_TAG_WHITELIST.update(_ADD_INLINE_0619)
    for _kw in _ADD_INLINE_0619:
        if _kw not in KOREAN_TAG_KEYWORDS:
            KOREAN_TAG_KEYWORDS.append(_kw)
except Exception:
    pass


def _story_text_0619(story: dict) -> str:
    return f"{story.get('title','')}\n{story.get('desc','')}\n{story.get('summary','')}\n{story.get('url','')}"


def _match_any_0619(text: str, patterns: list[str]) -> bool:
    return any(re.search(p, text or '', re.I) for p in patterns)


def _has_crypto_core_0619(text: str) -> bool:
    return _match_any_0619(text or '', [
        r'bitcoin|btc|ethereum|eth|xrp|ripple|xrpl|xlm|stellar|ada|cardano|trx|tron|bnb|bch|bitcoin cash|shib|shiba inu|usdc|usdt|stablecoin|crypto|cryptocurrency|blockchain|tokeni[sz]ation|defi|web3|cbdc|mica|custody|exchange|wallet|on-?chain',
        r'비트코인|이더리움|리플|스텔라|에이다|카르다노|트론|바이낸스코인|비트코인캐시|시바이누|스테이블코인|암호화폐|가상자산|블록체인|토큰화|디파이|웹3|디지털자산|디지털화폐|수탁|거래소|지갑|온체인'
    ])


def _is_price_or_market_noise_0619(raw: str) -> bool:
    low = (raw or '').lower()
    price_terms = [
        r'급등', r'급락', r'약세', r'강세', r'상승함', r'상승세', r'하락함', r'하락세',
        r'회복세', r'가격\s*회복', r'재진입', r'다시\s*진입', r'2주\s*최고',
        r'사상\s*최고', r'오르며', r'내리며', r'급등세', r'급락세',
        r'\bprice\b', r'\brebound\b', r'\brecovery\b', r'\bre-?enter', r'\btwo-?week high\b',
        r'\bsurge\b', r'\bspike\b', r'\bjump\b', r'\brally\b', r'\bplunge\b', r'\bdrop\b',
        r'\bbearish\b', r'\bbullish\b', r'\bweakness\b', r'\bfud\b',
        r'시장\s*약화', r'시장\s*fud', r'시장\s*공포', r'재진입.*회복', r'회복.*확인'
    ]
    chart_terms = [
        r'지지선', r'저항선', r'목표가', r'차트', r'기술적\s*분석',
        r'\bsupport\b', r'\bresistance\b', r'\bchart\b', r'\btechnical analysis\b',
    ]
    return _match_any_0619(low, price_terms + chart_terms)


def _is_wallet_metric_noise_0619(raw: str) -> bool:
    low = (raw or '').lower()
    return _match_any_0619(low, [
        r'지갑이\s*늘', r'지갑이\s*줄', r'지갑\s*증가', r'지갑\s*감소',
        r'비어\s*있지\s*않은.*지갑', r'비어있지\s*않은.*지갑',
        r'non-?empty\s+wallet', r'wallets?\s+(?:increased|decreased|rose|fell|grew|declined)',
        r'network\s+growth', r'active\s+addresses?', r'주소\s*증가', r'활성\s*주소',
        r'santiment', r'샌티먼트에\s*따르면'
    ])


def _is_transfer_withdrawal_noise_0619(raw: str) -> bool:
    low = (raw or '').lower()
    return _match_any_0619(low, [
        r'이체함', r'이체\s*기록', r'이체했', r'옮김', r'옮겼', r'전송함',
        r'출금함', r'출금\s*기록', r'출금했', r'withdraw', r'withdrawal',
        r'transfer(?:red|s)?\s+\d', r'move(?:d|s)?\s+\d', r'old\s+wallet',
        r'dormant\s+wallet', r'깨어난\s*지갑', r'휴면\s*지갑',
    ])


def _is_unwanted_article_0619(story: dict) -> tuple[bool, str]:
    raw = _story_text_0619(story)
    low = raw.lower()

    if _is_price_or_market_noise_0619(raw):
        return True, '가격/시황/급등락 제외'
    if _is_wallet_metric_noise_0619(raw):
        return True, '지갑증감/온체인수치 제외'
    if _is_transfer_withdrawal_noise_0619(raw):
        return True, '이체/출금/휴면지갑 제외'

    if _match_any_0619(low, [
        r'(bybit|바이비트).{0,80}(card|카드).{0,80}(welcome|reward|rewards|리워드|신규\s*이용자)',
        r'(welcome|reward|rewards|리워드|신규\s*이용자).{0,80}(bybit|바이비트).{0,80}(card|카드)',
        r'최대\s*120\s*usdt',
    ]):
        return True, '거래소카드/리워드홍보 제외'

    if _match_any_0619(low, [
        r'\bbmag\b', r'card\s*expo', r'trading\s*card', r'card\s*exhibition',
        r'카드\s*엑스포', r'카드\s*전시', r'트레이딩\s*카드', r'아트\s*프로그램',
        r'bitcoin\s*asia\s*2026.*card',
    ]):
        return True, '카드전시/행사 제외'

    if _match_any_0619(low, [
        r'sleepagotchi', r'web3\s*health', r'health\s*coach', r'sleep\s*data', r'nutrition\s*data',
        r'건강\s*코치', r'헬스\s*앱', r'수면.*영양',
        r'zetachain', r'zeta\s*chain', r'cross[-\s]*chain\s*service', r'크로스체인\s*서비스',
        r'제품\s*방향\s*재편', r'product\s*direction',
        r'anonymous\s+document\s+tracing', r'익명\s*문서\s*추적', r'검색\s*범위',
        r'비탈릭.*익명\s*문서', r'13일째\s*성과',
    ]):
        return True, '웹3앱/비포폴체인/실험성 제외'

    if _match_any_0619(low, [
        r'survey', r'설문', r'wealthy\s*investors?', r'wealth\s*advis[oe]rs?',
        r'underexposed', r'crypto\s*exposure', r'소극적', r'노출도', r'투자자들은\s*여전히',
    ]):
        return True, '설문/투자심리 제외'

    if _match_any_0619(low, [
        r'압박이\s*커지', r'마감\s*압박', r'deadline\s*pressure', r'negotiation\s*pressure',
        r'협상.*계속', r'talks?\s+continue', r'aug\.?\s*7\s*deadline', r'8월\s*7일\s*마감',
    ]):
        return True, '협상압박/과정기사 제외'

    if _match_any_0619(low, [
        r'bip-?110', r'luke\s*dashjr', r'철회\s*요구', r'논쟁\s*확대',
        r'withdrawal\s+calls?', r'proposal\s+debate',
    ]):
        return True, '기술논쟁/BIP 제외'

    if _match_any_0619(low, [
        r'(strategy|스트래티지|마이클\s*세일러|michael\s*saylor).{0,120}(sold|sell|sale|dispose|disposed|처분|매도)',
        r'(sold|sell|sale|dispose|disposed|처분|매도).{0,120}(strategy|스트래티지|마이클\s*세일러|michael\s*saylor)',
        r'3,?588\s*btc',
    ]):
        return True, '기업보유분매도/처분 제외'

    if _match_any_0619(low, [
        r'commercial\s*real\s*estate', r'office\s*space', r'multifamily', r'loan\s*portfolio',
        r'대출\s*포트폴리오', r'상업용\s*부동산', r'오피스\s*공실', r'부실\s*자산', r'익스포저',
    ]):
        return True, '부동산/대출포트폴리오 제외'

    general_non_crypto = _match_any_0619(low, [
        r'sk\s*hynix', r'sk하이닉스', r'나스닥\s*데뷔', r'공모\s*물량', r'인수\s*가능성',
        r'lg\b', r'공정거래위원회', r'상생협약', r'납품대금', r'협력사',
        r'그린\s*하버', r'데이터센터.*전력', r'gpu\s*병목', r'상생경제', r'상생\s*결제',
    ])
    if general_non_crypto and not _has_crypto_core_0619(low):
        return True, '비크립토 일반산업/주식 제외'

    ai_general = _match_any_0619(low, [
        r'ai\s*사업부', r'ai\s*산업화', r'ai\s*규제', r'ai\s*챗봇', r'동반자형\s*챗봇',
        r'ai\s*데이터센터', r'gpu\s*병목'
    ])
    crypto_or_major_policy = _has_crypto_core_0619(low) or _match_any_0619(low, [
        r'openai', r'microsoft', r'anthropic', r'bytedance', r'alibaba', r'중국.*ai\s*규제'
    ])
    if ai_general and not crypto_or_major_policy:
        return True, '일반AI/비크립토 제외'

    return False, ''


try:
    _PREV_matches_keywords_0619 = matches_keywords
    def matches_keywords(story: dict, coins: list[str], econ_keywords: list[str], korean_keywords: list[str]) -> bool:
        blocked, reason = _is_unwanted_article_0619(story)
        if blocked:
            print(f'[{reason}] {story.get("title", "")}')
            return False
        return _PREV_matches_keywords_0619(story, coins, econ_keywords, korean_keywords)
except Exception:
    pass


_EVENT_MARKER_PATTERNS_0619 = {
    'evt_bybit_card_welcome_reward': [
        r'(bybit|바이비트).{0,100}(card|카드).{0,100}(welcome|reward|rewards|리워드|120\s*usdt)',
        r'(welcome|reward|rewards|리워드|120\s*usdt).{0,100}(bybit|바이비트).{0,100}(card|카드)',
    ],
    'evt_worldcup_prediction_market': [
        r'(world\s*cup|월드컵|축구).{0,120}(prediction\s*market|predict|예측시장|예측\s*시장)',
        r'(prediction\s*market|predict|예측시장|예측\s*시장).{0,120}(world\s*cup|월드컵|축구)',
    ],
    'evt_xrpl_lending_protocol_0619': [
        r'(xrp\s*ledger|xrpl|xrpledger|리플|xrp).{0,120}(lending|loan|loans|yield|yields|대출|수익)',
        r'(lending|loan|loans|yield|yields|대출|수익).{0,120}(xrp\s*ledger|xrpl|xrpledger|리플|xrp)',
    ],
    'evt_openusd_upbit_standards': [
        r'(openusd|오픈usd|open\s*usd).{0,140}(upbit|업비트|standard|스탠더드|스탠다드)',
        r'(upbit|업비트).{0,140}(openusd|오픈usd|open\s*usd)',
    ],
    'evt_bitmine_eth_tomlee_purchase': [
        r'(bitmine|비트마인|tom\s*lee|톰리).{0,140}(eth|ethereum|이더리움).{0,80}(purchase|buy|매수|매입|확보)',
        r'(eth|ethereum|이더리움).{0,120}(bitmine|비트마인|tom\s*lee|톰리).{0,80}(purchase|buy|매수|매입|확보)',
    ],
    'evt_fca_crypto_rules_2027': [
        r'(fca|영국|financial\s*conduct\s*authority).{0,120}(2027|final|rules|regulation|규제|공개)',
        r'(2027|final|rules|regulation|규제|공개).{0,120}(fca|영국|financial\s*conduct\s*authority)',
    ],
    'evt_russia_digital_ruble_2026': [
        r'(russia|러시아|central\s*bank|중앙은행).{0,120}(digital\s*ruble|digital\s*rouble|디지털\s*루블)',
        r'(digital\s*ruble|digital\s*rouble|디지털\s*루블).{0,120}(russia|러시아|central\s*bank|중앙은행)',
    ],
}


def _extract_event_markers_0619(text: str) -> list[str]:
    raw = text or ''
    found = []
    for marker, patterns in _EVENT_MARKER_PATTERNS_0619.items():
        if _match_any_0619(raw, patterns):
            found.append(marker)
    return sorted(set(found))


def _append_event_markers_0619(base_key: str, story: dict) -> str:
    parts = [p.strip() for p in (base_key or '').split('|') if p.strip()]
    parts.extend(_extract_event_markers_0619(_story_text_0619(story)))
    generic = {
        'action_partner', 'topic_partnership', 'action_buy', 'topic_purchase',
        'action_launch', 'topic_launch', 'action_approve', 'topic_approval',
        'action_restrict', 'topic_fed_rate', 'topic_treasury', 'geo_us', 'geo_eu', 'year_2026', 'org_sec'
    }
    has_event = any(p.startswith('evt_') for p in parts)
    if not has_event:
        non_generic = [p for p in parts if p not in generic]
        if len(non_generic) < 3:
            parts = non_generic
    seen = set(); out = []
    for p in sorted(parts):
        if p and p not in seen:
            out.append(p); seen.add(p)
    return ' | '.join(out)


try:
    _PREV_build_story_signature_0619 = build_story_signature
    _PREV_build_canonical_topic_key_0619 = build_canonical_topic_key
    def build_story_signature(story: dict) -> str:
        return _append_event_markers_0619(_PREV_build_story_signature_0619(story), story)
    def build_canonical_topic_key(story: dict) -> str:
        return _append_event_markers_0619(_PREV_build_canonical_topic_key_0619(story), story)
except Exception:
    pass


def _tokens_0619(key: str) -> set:
    return {x.strip() for x in (key or '').split('|') if x.strip()}


def _event_tokens_0619(key: str) -> set:
    return {t for t in _tokens_0619(key) if t.startswith('evt_')}


def _specific_tokens_0619(key: str) -> set:
    generic = {
        'action_partner', 'topic_partnership', 'action_buy', 'topic_purchase',
        'action_launch', 'topic_launch', 'action_approve', 'topic_approval',
        'action_restrict', 'topic_fed_rate', 'topic_treasury', 'geo_us', 'geo_eu', 'year_2026', 'org_sec'
    }
    return {t for t in _tokens_0619(key) if t not in generic}


try:
    def is_canonical_duplicate(canonical_key: str, seen_keys: set[str]) -> bool:
        if not canonical_key:
            return False
        cur_events = _event_tokens_0619(canonical_key)
        cur_specific = _specific_tokens_0619(canonical_key)
        for old_key in seen_keys:
            old_events = _event_tokens_0619(old_key)
            shared_events = cur_events & old_events
            if shared_events:
                log(f'[이벤트중복 제외 0619] shared_event={shared_events}')
                return True
            old_specific = _specific_tokens_0619(old_key)
            shared = cur_specific & old_specific
            same_entity = any(t.startswith(('entity_', 'org_', 'person_', 'bill_')) for t in shared)
            same_asset = any(t.startswith('asset_') for t in shared)
            same_topic = any(t.startswith('topic_') for t in shared)
            same_action = any(t.startswith(('action_', 'act_')) for t in shared)
            if same_entity and same_asset and same_topic and same_action:
                log(f'[정규토픽중복 제외 0619] shared_specific={shared}')
                return True
        return False

    def is_semantically_duplicate(story: dict, seen_signatures: list[str], seen_titles: list[str]) -> bool:
        title = normalize_for_duplicate(story.get('title', ''))
        signature = build_story_signature(story)
        for old_title in seen_titles:
            ratio = SequenceMatcher(None, title, old_title).ratio()
            if ratio >= 0.90:
                log(f'[제목유사도 중복 0619] {title} <> {old_title} / {ratio:.2f}')
                return True
        cur_events = _event_tokens_0619(signature)
        cur_specific = _specific_tokens_0619(signature)
        for old_sig in seen_signatures:
            old_events = _event_tokens_0619(old_sig)
            shared_events = cur_events & old_events
            if shared_events:
                log(f'[이벤트중복 제외 0619] shared_event={shared_events}')
                return True
            old_specific = _specific_tokens_0619(old_sig)
            shared = cur_specific & old_specific
            same_entity = any(t.startswith(('entity_', 'org_', 'person_', 'bill_')) for t in shared)
            same_asset = any(t.startswith('asset_') for t in shared)
            same_topic = any(t.startswith('topic_') for t in shared)
            same_action = any(t.startswith(('action_', 'act_')) for t in shared)
            if same_entity and same_asset and same_topic and same_action:
                log(f'[의미중복 제외 0619] shared_specific={shared}')
                return True
        return False
except Exception:
    pass


_INLINE_BODY_TAG_SPECS_0619 = [
    ('폴리마켓', [r'polymarket', r'폴리마켓']),
    ('카세스', [r'caceis', r'카세스']),
    ('메리아', [r'\bmeria\b', r'메리아']),
    ('인도', [r'\bindia\b', r'indian', r'인도']),
    ('마이크론', [r'\bmicron\b', r'micron technology', r'마이크론']),
    ('IMF', [r'\bimf\b', r'국제통화기금']),
    ('독일', [r'\bgermany\b', r'german', r'독일']),
    ('카르다노', [r'\bcardano\b', r'\bada\b', r'카르다노', r'에이다']),
    ('두바이', [r'\bdubai\b', r'두바이']),
    ('알리바바', [r'alibaba', r'알리바바']),
    ('마이클세일러', [r'michael\s*saylor', r'\bsaylor\b', r'마이클\s*세일러', r'마이클세일러']),
    ('톰리', [r'tom\s*lee', r'thomas\s*lee', r'톰\s*리', r'톰리']),
    ('비트마인', [r'bitmine', r'비트마인']),
    ('시장구조법안', [r'market\s*structure\s*bill', r'clarity\s*act', r'시장\s*구조\s*법안', r'시장구조법안', r'클래리티법']),
    ('바이비트', [r'bybit', r'바이비트']),
    ('업비트', [r'upbit', r'업비트']),
    ('바이낸스', [r'binance', r'바이낸스']),
    ('필리핀', [r'philippines', r'필리핀']),
    ('중국', [r'\bchina\b', r'chinese', r'중국']),
    ('러시아', [r'\brussia\b', r'russian', r'러시아']),
    ('중앙은행', [r'central\s*bank', r'중앙은행']),
    ('디지털루블', [r'digital\s*ruble', r'digital\s*rouble', r'디지털\s*루블', r'디지털루블']),
    ('마이크로소프트', [r'microsoft', r'마이크로소프트']),
]


def _restore_korean_inline_tags_0619(summary: str, story: dict, max_tags: int = 5) -> str:
    if not summary:
        return summary
    raw = _story_text_0619(story)
    base = f'{summary}\n{raw}'
    text = html.unescape(summary)
    labels = []
    for label, pats in _INLINE_BODY_TAG_SPECS_0619:
        if len(labels) >= max_tags:
            break
        if f'#{label}' in text:
            labels.append(label)
            continue
        if _match_any_0619(base, pats):
            labels.append(label)
    prefix = []
    for label in labels:
        if f'#{label}' in text:
            continue
        replaced = False
        for lab, pats in _INLINE_BODY_TAG_SPECS_0619:
            if lab != label:
                continue
            for pat in pats:
                new_text, cnt = re.subn(pat, f'#{label}', text, count=1, flags=re.I)
                if cnt:
                    text = new_text
                    replaced = True
                    break
            break
        if not replaced:
            prefix.append(f'#{label}')
    if prefix:
        lines = text.split('\n', 1)
        first = lines[0].strip()
        rest = lines[1] if len(lines) > 1 else ''
        first = (' '.join(prefix) + ' ' + first).strip()
        text = first + (('\n' + rest) if rest else '')
    return text


def _fix_summary_endings_0619(summary: str) -> str:
    text = html.unescape(summary or '')
    text = text.replace('#시장구조#법안', '#시장구조법안')
    text = text.replace('#시장구조 #법안', '#시장구조법안')
    text = text.replace('#시장구조법안 가', '#시장구조법안 이')
    text = text.replace('#시장구조법안가', '#시장구조법안 이')
    text = text.replace('#법안 가', '#법안 이')
    text = text.replace('#AI 가', '#AI가')
    text = text.replace('#마이클#세일러', '#마이클세일러')
    text = text.replace('#톰#리', '#톰리')

    text = re.sub(r'했음\s*고\s*(전함|말함|밝힘|함)?', '했음', text)
    text = re.sub(r'했음고(전함|말함|밝힘|함)?', '했음', text)
    text = re.sub(r'됐음\s*고\s*(전함|말함|밝힘|함)?', '됐음', text)
    text = re.sub(r'됨고(전함|말함|밝힘|함)?', '됨', text)
    text = re.sub(r'([가-힣]+)했다고\s*함', r'\1했음', text)
    text = re.sub(r'([가-힣]+)했다고\s*전함', r'\1했음', text)
    text = re.sub(r'([가-힣]+)했다고\s*밝힘', r'\1했음', text)

    text = re.sub(r'([가-힣]+)했\.', r'\1함', text)
    text = re.sub(r'([가-힣]+)했다\.', r'\1함', text)
    text = re.sub(r'([가-힣]+)했습니다\.', r'\1함', text)
    text = re.sub(r'했습니다(?=($|\s|[.!?\n]))', '함', text)
    text = re.sub(r'했다(?=($|\s|[.!?\n]))', '함', text)
    text = re.sub(r'하였다(?=($|\s|[.!?\n]))', '함', text)
    text = re.sub(r'됐습니다(?=($|\s|[.!?\n]))', '됨', text)
    text = re.sub(r'됐다(?=($|\s|[.!?\n]))', '됨', text)
    text = re.sub(r'밝혔습니다(?=($|\s|[.!?\n]))', '밝힘', text)
    text = re.sub(r'밝혔다(?=($|\s|[.!?\n]))', '밝힘', text)
    text = re.sub(r'전했습니다(?=($|\s|[.!?\n]))', '전함', text)
    text = re.sub(r'전했다(?=($|\s|[.!?\n]))', '전함', text)
    text = re.sub(r'설명했습니다(?=($|\s|[.!?\n]))', '설명함', text)
    text = re.sub(r'설명했다(?=($|\s|[.!?\n]))', '설명함', text)

    lines = []
    for line in text.splitlines():
        line = line.strip()
        line = re.sub(r'[.。]+$', '', line)
        lines.append(line)
    text = '\n'.join(lines)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    return text


_FOOTER_TAG_TRANSLATE_0619 = {
    '#China': '#중국', '#Korea': '#한국', '#SouthKorea': '#한국', '#UK': '#영국', '#US': '#미국',
    '#Russia': '#러시아', '#Germany': '#독일', '#India': '#인도', '#Dubai': '#두바이',
    '#Cardano': '#카르다노', '#ADA': '#카르다노', '#Alibaba': '#알리바바', '#Micron': '#마이크론',
    '#Polymarket': '#폴리마켓', '#MichaelSaylor': '#마이클세일러', '#Saylor': '#마이클세일러',
    '#TomLee': '#톰리', '#Bitmine': '#비트마인', '#BitMine': '#비트마인',
    '#MarketStructureBill': '#시장구조법안', '#CLARITYAct': '#시장구조법안', '#Wallet': '', '#AI가': '#AI',
    '#Rates': '', '#Lending': '', '#Bank': '', '#Banks': '',
}


def _clean_footer_tags_0619(footer: str) -> str:
    tags = []
    seen = set()
    for raw in (footer or '').split():
        t = raw.strip()
        if not t:
            continue
        t = _FOOTER_TAG_TRANSLATE_0619.get(t, t)
        if not t:
            continue
        t = t.replace('#시장구조#법안', '#시장구조법안')
        if t in {'#Rate', '#Loan', '#Loans', '#Health', '#Sleep', '#Nutrition', '#Expo', '#Card', '#Cards'}:
            continue
        if t not in seen:
            tags.append(t)
            seen.add(t)
    return ' '.join(tags)


try:
    _PREV_build_message_0619_quality = build_message
    def build_message(story: dict) -> str:
        msg = _PREV_build_message_0619_quality(story)
        if not msg:
            return msg
        parts = msg.split('\n\n')
        if len(parts) >= 1:
            summary = html.unescape(parts[0])
            summary = _restore_korean_inline_tags_0619(summary, story, max_tags=5)
            summary = _fix_summary_endings_0619(summary)
            parts[0] = html.escape(summary)
        if len(parts) >= 4:
            parts[-1] = _clean_footer_tags_0619(parts[-1])
        return '\n\n'.join(p for p in parts if p.strip())
except Exception:
    pass




# =========================
# 0620 general duplicate engine patch
# 목적:
# - 특정 예시 기사만 하드코딩해서 잡는 방식이 아니라,
#   앞으로 들어오는 모든 기사에 대해 "이벤트 단위"로 중복을 잡도록 보강
# - 같은 사건이 다른 매체/다른 제목으로 반복될 때
#   entity + topic + action + asset/country/amount 조합으로 중복 판정
# - 너무 넓은 topic_partnership/topic_purchase/topic_fed_rate 같은 토큰만으로 과차단하지 않음
# =========================

_GENERIC_DUP_TOKENS_0620 = {
    'action_partner', 'topic_partnership', 'action_buy', 'topic_purchase',
    'action_launch', 'topic_launch', 'action_approve', 'topic_approval',
    'action_restrict', 'topic_fed_rate', 'topic_treasury', 'topic_defi',
    'topic_ai', 'topic_regulation', 'topic_법안',
    'act_approval', 'act_buy', 'act_move', 'act_adoption', 'act_policy',
    'geo_us', 'geo_eu', 'year_2026', 'year_2027', 'org_sec',
    'org_treasury', 'asset_btc'
}

_SOURCE_NOISE_0620 = {
    'cointelegraph', 'cryptopolitan', 'thecryptobasic', 'cryptobasic',
    'tokenpost', 'bitcoinist', 'coinedition', 'cryptopotato',
    'thenewscrypto', 'utoday', 'u today', 'crypto news', 'cryptonews',
    'news', 'today', 'update', 'latest', 'report', 'reports',
    'article', 'post', 'market', 'markets'
}

_ENTITY_ALIAS_PATTERNS_0620 = {
    # 규제기관/공공기관
    'entity_sec': [r'(?<![a-z0-9])sec(?![a-z0-9])', r'securities and exchange commission', r'증권거래위원회'],
    'entity_cftc': [r'(?<![a-z0-9])cftc(?![a-z0-9])'],
    'entity_fca': [r'(?<![a-z0-9])fca(?![a-z0-9])', r'financial conduct authority'],
    'entity_occ': [r'(?<![a-z0-9])occ(?![a-z0-9])'],
    'entity_hkma': [r'(?<![a-z0-9])hkma(?![a-z0-9])', r'hong kong monetary authority', r'홍콩금융관리국'],
    'entity_imf': [r'(?<![a-z0-9])imf(?![a-z0-9])', r'국제통화기금'],
    'entity_fed': [r'(?<![a-z0-9])fed(?![a-z0-9])', r'federal reserve', r'연준'],
    'entity_centralbank': [r'central bank', r'중앙은행'],

    # 회사/프로젝트/인물
    'entity_bybit': [r'bybit', r'바이비트'],
    'entity_binance': [r'binance', r'바이낸스'],
    'entity_upbit': [r'upbit', r'업비트'],
    'entity_bitmine': [r'bitmine', r'비트마인'],
    'entity_strategy': [r'(?<![a-z0-9])strategy(?![a-z0-9])', r'microstrategy', r'스트래티지'],
    'entity_michaelsaylor': [r'michael saylor', r'마이클\s*세일러', r'마이클세일러'],
    'entity_tomlee': [r'tom lee', r'thomas lee', r'톰\s*리', r'톰리'],
    'entity_ripple': [r'(?<![a-z0-9])ripple(?![a-z0-9])', r'리플'],
    'entity_xrpledger': [r'xrp ledger', r'xrpl', r'xrpledger'],
    'entity_polymarket': [r'polymarket', r'폴리마켓'],
    'entity_microsoft': [r'microsoft', r'마이크로소프트'],
    'entity_openai': [r'openai', r'오픈ai', r'오픈에이아이'],
    'entity_anthropic': [r'anthropic', r'앤트로픽'],
    'entity_google': [r'google', r'구글'],
    'entity_blackrock': [r'blackrock', r'블랙록'],
    'entity_mastercard': [r'mastercard', r'마스터카드'],
    'entity_jpmorgan': [r'j\.?p\.?\s*morgan', r'jpmorgan', r'제이피모건', r'jp모건'],
    'entity_cardano': [r'cardano', r'카르다노'],
    'entity_worldcup': [r'world cup', r'fifa', r'월드컵', r'축구'],
    'entity_caceis': [r'caceis', r'카세스'],
    'entity_meria': [r'(?<![a-z0-9])meria(?![a-z0-9])', r'메리아'],
    'entity_micron': [r'micron', r'마이크론'],
    'entity_alibaba': [r'alibaba', r'알리바바'],
}

_ASSET_PATTERNS_0620 = {
    'asset_btc': [r'(?<![a-z0-9])btc(?![a-z0-9])', r'bitcoin', r'비트코인'],
    'asset_eth': [r'(?<![a-z0-9])eth(?![a-z0-9])', r'ethereum', r'이더리움'],
    'asset_xrp': [r'(?<![a-z0-9])xrp(?![a-z0-9])', r'(?<![a-z0-9])ripple(?![a-z0-9])', r'리플'],
    'asset_xrpl': [r'xrp ledger', r'xrpl', r'xrpledger'],
    'asset_ada': [r'(?<![a-z0-9])ada(?![a-z0-9])', r'cardano', r'카르다노', r'에이다'],
    'asset_usdt': [r'(?<![a-z0-9])usdt(?![a-z0-9])'],
    'asset_usdc': [r'(?<![a-z0-9])usdc(?![a-z0-9])'],
    'asset_stablecoin': [r'stablecoin', r'stablecoins', r'스테이블코인'],
    'asset_cbdc': [r'(?<![a-z0-9])cbdc(?![a-z0-9])', r'디지털화폐', r'디지털통화'],
}

_GEO_PATTERNS_0620 = {
    'geo_us': [r'united states', r'(?<![a-z0-9])u\.?s\.?(?![a-z0-9])', r'(?<![a-z0-9])usa(?![a-z0-9])', r'미국'],
    'geo_uk': [r'united kingdom', r'(?<![a-z0-9])uk(?![a-z0-9])', r'britain', r'영국'],
    'geo_korea': [r'south korea', r'(?<![a-z0-9])korea(?![a-z0-9])', r'한국'],
    'geo_japan': [r'japan', r'일본'],
    'geo_china': [r'china', r'chinese', r'중국'],
    'geo_hongkong': [r'hong kong', r'홍콩'],
    'geo_russia': [r'russia', r'russian', r'러시아'],
    'geo_india': [r'india', r'indian', r'인도'],
    'geo_germany': [r'germany', r'german', r'독일'],
    'geo_dubai': [r'dubai', r'두바이'],
    'geo_philippines': [r'philippines', r'필리핀'],
}

_TOPIC_PATTERNS_0620 = {
    'topic_card_reward': [r'card', r'카드', r'welcome reward', r'리워드', r'신규 이용자'],
    'topic_prediction_market': [r'prediction market', r'prediction markets', r'예측시장', r'예측 시장'],
    'topic_lending': [r'lending', r'loan', r'loans', r'대출', r'loan protocol', r'대출 프로토콜'],
    'topic_stablecoin': [r'stablecoin', r'stablecoins', r'스테이블코인'],
    'topic_cbdc': [r'(?<![a-z0-9])cbdc(?![a-z0-9])', r'디지털화폐', r'디지털통화'],
    'topic_digital_ruble': [r'digital ruble', r'digital rouble', r'디지털 루블', r'디지털루블'],
    'topic_regulation': [r'regulation', r'rule', r'rules', r'regulated', r'규제', r'규칙'],
    'topic_approval': [r'approval', r'approved', r'approve', r'승인', r'인가'],
    'topic_sandbox': [r'sandbox', r'샌드박스'],
    'topic_mica': [r'(?<![a-z0-9])mica(?![a-z0-9])', r'미카'],
    'topic_custody': [r'custody', r'custodial', r'수탁'],
    'topic_etf': [r'(?<![a-z0-9])etf(?![a-z0-9])'],
    'topic_treasury': [r'treasury', r'재무', r'재무부', r'기업보유', r'corporate treasury'],
    'topic_bill': [r'bill', r'act', r'law', r'법안'],
    'topic_market_structure_bill': [r'market structure bill', r'clarity act', r'시장구조법안', r'시장 구조 법안', r'클래리티법'],
    'topic_ai': [r'(?<![a-z0-9])ai(?![a-z0-9])', r'artificial intelligence', r'인공지능'],
    'topic_partnership': [r'partnership', r'partner', r'제휴', r'협력', r'협약'],
    'topic_purchase': [r'purchase', r'buy', r'bought', r'매수', r'매입', r'확보'],
    'topic_sale': [r'sell', r'sold', r'sale', r'dispose', r'disposed', r'처분', r'매도'],
    'topic_wallet': [r'wallet', r'지갑'],
    'topic_transfer': [r'transfer', r'withdraw', r'withdrawal', r'이체', r'출금'],
}

_ACTION_PATTERNS_0620 = {
    'action_launch': [r'launch', r'launched', r'roll out', r'출시', r'공개', r'도입'],
    'action_approve': [r'approval', r'approved', r'approve', r'승인', r'인가'],
    'action_probe': [r'probe', r'investigat', r'조사'],
    'action_ban_restrict': [r'ban', r'restrict', r'prohibit', r'금지', r'제한'],
    'action_buy': [r'purchase', r'buy', r'bought', r'매수', r'매입', r'확보'],
    'action_sell': [r'sell', r'sold', r'sale', r'dispose', r'disposed', r'처분', r'매도'],
    'action_partner': [r'partnership', r'partner', r'제휴', r'협력', r'협약'],
    'action_file': [r'filed', r'filing', r'신청', r'제출', r'신고'],
    'action_urge': [r'urge', r'call for', r'촉구', r'요구'],
}


def _norm_0620(text: str) -> str:
    try:
        return normalize_for_duplicate(text or "")
    except Exception:
        t = (text or "").lower()
        t = re.sub(r'https?://\S+', ' ', t)
        t = re.sub(r'[^a-z0-9가-힣\s]', ' ', t)
        return re.sub(r'\s+', ' ', t).strip()


def _has_pat_0620(raw: str, patterns: list[str]) -> bool:
    return any(re.search(p, raw or "", re.I) for p in patterns)


def _collect_by_patterns_0620(raw: str, table: dict) -> set:
    out = set()
    for key, patterns in table.items():
        if _has_pat_0620(raw, patterns):
            out.add(key)
    return out


def _proper_entity_tokens_0620(title: str) -> set:
    out = set()
    title = title or ""
    candidates = re.findall(r'\b[A-Z][A-Za-z0-9&.-]*(?:\s+[A-Z][A-Za-z0-9&.-]*){0,3}\b', title)

    for cand in candidates:
        c = cand.strip()
        if not c:
            continue
        low = c.lower()
        if low in _SOURCE_NOISE_0620:
            continue
        if len(low) <= 2 and low not in {'ai', 'uk', 'us'}:
            continue

        # 너무 일반적인 단어 제거
        if low in {'crypto', 'bitcoin', 'ethereum', 'stablecoin', 'defi', 'web3', 'today', 'news'}:
            continue

        try:
            mapped = MANUAL_TRANSLATIONS.get(c, c)
        except Exception:
            mapped = c

        token = re.sub(r'[^a-zA-Z0-9가-힣]+', '', str(mapped)).lower()
        if token and token not in {'암호화폐', '비트코인', '이더리움'}:
            out.add(f'entity_{token}')

    return out


def _number_tokens_0620(raw: str) -> set:
    out = set()
    low = (raw or "").lower()

    # 날짜/연도/큰 금액/큰 수량만 사용
    for y in re.findall(r'\b20[2-9][0-9]\b', low):
        out.add(f'year_{y}')

    # 8월 7일, July 7 등
    for m, d in re.findall(r'(\d{1,2})\s*월\s*(\d{1,2})\s*일', low):
        out.add(f'date_{m}_{d}')
    for month, day in re.findall(r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*(\d{1,2})\b', low):
        out.add(f'date_{month}_{day}')

    # 금액/수량은 너무 세세하게 말고 대표값만
    amount_patterns = [
        r'(\d+(?:\.\d+)?)\s*(billion|million)\s*(?:dollars?|usd)',
        r'(\d+(?:,\d{3})+|\d+)\s*(btc|eth|xrp|usdt|usdc)',
        r'(\d+(?:억|조))\s*(?:달러|원)?',
    ]
    for pat in amount_patterns:
        for m in re.finditer(pat, low, re.I):
            token = re.sub(r'[^a-z0-9가-힣]+', '', m.group(0).lower())
            if token:
                out.add(f'num_{token[:24]}')
            if len(out) >= 3:
                break

    return out


def _event_profile_0620_from_story(story: dict) -> dict:
    raw_original = f"{story.get('title','')}\n{story.get('desc','')}\n{story.get('url','')}"
    raw = _norm_0620(raw_original)
    title = story.get('title', '') or ""

    entities = _collect_by_patterns_0620(raw, _ENTITY_ALIAS_PATTERNS_0620)
    entities |= _proper_entity_tokens_0620(title)

    assets = _collect_by_patterns_0620(raw, _ASSET_PATTERNS_0620)
    geos = _collect_by_patterns_0620(raw, _GEO_PATTERNS_0620)
    topics = _collect_by_patterns_0620(raw, _TOPIC_PATTERNS_0620)
    actions = _collect_by_patterns_0620(raw, _ACTION_PATTERNS_0620)
    nums = _number_tokens_0620(raw)

    # 자산/회사에서 너무 흔한 BTC만 있는 경우 중복 판단에 쓰지 않도록 약화
    if assets == {'asset_btc'} and not (entities or topics or actions):
        assets = set()

    return {
        'entities': entities,
        'assets': assets,
        'geos': geos,
        'topics': topics,
        'actions': actions,
        'nums': nums,
    }


def _profile_tokens_0620(profile: dict) -> set:
    toks = set()
    for k in ('entities', 'assets', 'geos', 'topics', 'actions', 'nums'):
        toks |= set(profile.get(k, set()))
    return toks


def _event_fingerprint_0620_from_profile(profile: dict) -> str:
    entities = sorted(profile.get('entities', set()))
    assets = sorted(profile.get('assets', set()))
    geos = sorted(profile.get('geos', set()))
    topics = sorted(profile.get('topics', set()))
    actions = sorted(profile.get('actions', set()))
    nums = sorted(profile.get('nums', set()))

    # 중복 판단 가능한 최소 조건
    has_subject = bool(entities or assets or geos)
    has_event = bool(topics or actions)
    if not (has_subject and has_event):
        return ""

    # 너무 일반적인 BTC + AI 같은 경우는 fingerprint 생성하지 않음
    if not entities and assets <= {'asset_btc'} and topics <= {'topic_ai'}:
        return ""

    core = []
    core.extend(entities[:4])
    core.extend(assets[:3])
    core.extend(geos[:2])
    core.extend(topics[:4])
    core.extend(actions[:3])

    # 날짜/큰 금액은 보조 식별자로 2개까지만
    core.extend(nums[:2])

    core = [x for x in core if x and x not in _GENERIC_DUP_TOKENS_0620]
    if len(core) < 3:
        return ""

    raw_key = "|".join(sorted(set(core)))
    # 사람이 로그에서 보기 좋게 앞부분을 남김
    clean = re.sub(r'[^a-z0-9가-힣_]+', '_', raw_key.lower()).strip('_')
    return "eventfp_" + clean[:180]


def _event_fingerprint_0620(story: dict) -> str:
    return _event_fingerprint_0620_from_profile(_event_profile_0620_from_story(story))


def _split_key_0620(key: str) -> set:
    return {x.strip() for x in (key or "").split("|") if x.strip()}


def _events_from_key_0620(key: str) -> set:
    return {t for t in _split_key_0620(key) if t.startswith("evt_") or t.startswith("eventfp_")}


def _specific_from_key_0620(key: str) -> set:
    return {t for t in _split_key_0620(key) if t and t not in _GENERIC_DUP_TOKENS_0620}


try:
    _PREV_build_story_signature_0620 = build_story_signature
    _PREV_build_canonical_topic_key_0620 = build_canonical_topic_key

    def build_story_signature(story: dict) -> str:
        base = _PREV_build_story_signature_0620(story)
        parts = [p.strip() for p in (base or "").split("|") if p.strip()]
        fp = _event_fingerprint_0620(story)
        if fp:
            parts.append(fp)
        # 프로필의 핵심 토큰도 signature에 포함해 이후 비교 가능하게 저장
        prof = _event_profile_0620_from_story(story)
        parts.extend(sorted(_profile_tokens_0620(prof) - _GENERIC_DUP_TOKENS_0620))
        seen = set()
        out = []
        for p in sorted(parts):
            if p and p not in seen:
                out.append(p)
                seen.add(p)
        return " | ".join(out)

    def build_canonical_topic_key(story: dict) -> str:
        base = _PREV_build_canonical_topic_key_0620(story)
        parts = [p.strip() for p in (base or "").split("|") if p.strip()]
        fp = _event_fingerprint_0620(story)
        if fp:
            parts.append(fp)
        prof = _event_profile_0620_from_story(story)
        parts.extend(sorted(_profile_tokens_0620(prof) - _GENERIC_DUP_TOKENS_0620))
        seen = set()
        out = []
        for p in sorted(parts):
            if p and p not in seen:
                out.append(p)
                seen.add(p)
        return " | ".join(out)
except Exception:
    pass


def _is_same_event_by_tokens_0620(cur_key: str, old_key: str) -> bool:
    cur_events = _events_from_key_0620(cur_key)
    old_events = _events_from_key_0620(old_key)

    # exact event fingerprint / known event marker
    shared_events = cur_events & old_events
    if shared_events:
        log(f"[이벤트중복 제외 0620] shared_event={shared_events}")
        return True

    cur = _specific_from_key_0620(cur_key)
    old = _specific_from_key_0620(old_key)
    shared = cur & old

    if not shared:
        return False

    shared_entities = {t for t in shared if t.startswith(('entity_', 'org_', 'person_', 'bill_'))}
    shared_assets = {t for t in shared if t.startswith('asset_')}
    shared_geos = {t for t in shared if t.startswith('geo_')}
    shared_topics = {t for t in shared if t.startswith('topic_')}
    shared_actions = {t for t in shared if t.startswith(('action_', 'act_'))}
    shared_nums = {t for t in shared if t.startswith(('num_', 'date_', 'year_'))}

    # 가장 안정적인 조건들
    if shared_entities and shared_topics and (shared_actions or shared_assets or shared_geos or shared_nums):
        log(f"[일반중복 제외 0620] shared={shared}")
        return True

    if shared_assets and shared_topics and shared_actions and (shared_entities or shared_geos or shared_nums):
        log(f"[자산이벤트중복 제외 0620] shared={shared}")
        return True

    if shared_geos and shared_topics and shared_actions and (shared_entities or shared_assets or shared_nums):
        log(f"[지역이벤트중복 제외 0620] shared={shared}")
        return True

    # 주체가 매우 구체적이고 topic 2개 이상 겹치면 중복
    if shared_entities and len(shared_topics) >= 2:
        log(f"[주체토픽중복 제외 0620] shared={shared}")
        return True

    return False


try:
    def is_canonical_duplicate(canonical_key: str, seen_keys: set[str]) -> bool:
        if not canonical_key:
            return False
        for old_key in seen_keys:
            if _is_same_event_by_tokens_0620(canonical_key, old_key):
                return True
        return False

    def is_semantically_duplicate(story: dict, seen_signatures: list[str], seen_titles: list[str]) -> bool:
        title = _norm_0620(story.get('title', ''))
        signature = build_story_signature(story)

        # 제목 유사도는 전체적으로 적용하되 너무 낮게 잡지 않음
        for old_title in seen_titles:
            ratio = SequenceMatcher(None, title, old_title).ratio()
            if ratio >= 0.90:
                log(f"[제목유사도 중복 0620] {title} <> {old_title} / {ratio:.2f}")
                return True

            # 단어 Jaccard: 제목 어순이 달라도 같은 기사면 잡기
            cur_words = {w for w in title.split() if len(w) >= 3 and w not in _SOURCE_NOISE_0620}
            old_words = {w for w in (old_title or "").split() if len(w) >= 3 and w not in _SOURCE_NOISE_0620}
            if cur_words and old_words:
                inter = cur_words & old_words
                union = cur_words | old_words
                jacc = len(inter) / max(1, len(union))
                if len(inter) >= 4 and jacc >= 0.58:
                    log(f"[제목단어중복 0620] shared_words={inter} / jacc={jacc:.2f}")
                    return True

        for old_sig in seen_signatures:
            if _is_same_event_by_tokens_0620(signature, old_sig):
                return True

        return False
except Exception:
    pass



from doorinews_editor import install_editor_overrides

install_editor_overrides(globals())


if __name__ == '__main__':
    main()
