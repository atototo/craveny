--
-- PostgreSQL database dump
--

\restrict X57LTFQU4AukHGKuEqMLngmwahywIYWLf99x7CSohSxAwWmvqj9lNjOd94sPMCY

-- Dumped from database version 13.22
-- Dumped by pg_dump version 13.22

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: contenttype; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.contenttype AS ENUM (
    'news',
    'reddit',
    'twitter',
    'telegram'
);


ALTER TYPE public.contenttype OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: ab_test_config; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ab_test_config (
    id integer NOT NULL,
    model_a_id integer NOT NULL,
    model_b_id integer NOT NULL,
    is_active boolean DEFAULT false NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    CONSTRAINT different_models CHECK ((model_a_id <> model_b_id))
);


ALTER TABLE public.ab_test_config OWNER TO postgres;

--
-- Name: ab_test_config_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.ab_test_config_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.ab_test_config_id_seq OWNER TO postgres;

--
-- Name: ab_test_config_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.ab_test_config_id_seq OWNED BY public.ab_test_config.id;


--
-- Name: daily_model_performance; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.daily_model_performance (
    id integer NOT NULL,
    model_id integer NOT NULL,
    date date NOT NULL,
    total_predictions integer DEFAULT 0 NOT NULL,
    evaluated_count integer DEFAULT 0 NOT NULL,
    human_evaluated_count integer DEFAULT 0 NOT NULL,
    avg_final_score double precision,
    avg_auto_score double precision,
    avg_human_score double precision,
    avg_target_accuracy double precision,
    avg_timing_score double precision,
    avg_risk_management double precision,
    target_achieved_rate double precision,
    support_breach_rate double precision,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.daily_model_performance OWNER TO postgres;

--
-- Name: daily_model_performance_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.daily_model_performance_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.daily_model_performance_id_seq OWNER TO postgres;

--
-- Name: daily_model_performance_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.daily_model_performance_id_seq OWNED BY public.daily_model_performance.id;


--
-- Name: evaluation_history; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.evaluation_history (
    id integer NOT NULL,
    evaluation_id integer NOT NULL,
    old_human_rating_quality integer,
    old_human_rating_usefulness integer,
    old_human_rating_overall integer,
    old_final_score double precision,
    new_human_rating_quality integer,
    new_human_rating_usefulness integer,
    new_human_rating_overall integer,
    new_final_score double precision,
    modified_by text NOT NULL,
    modified_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    reason text
);


ALTER TABLE public.evaluation_history OWNER TO postgres;

--
-- Name: evaluation_history_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.evaluation_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.evaluation_history_id_seq OWNER TO postgres;

--
-- Name: evaluation_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.evaluation_history_id_seq OWNED BY public.evaluation_history.id;


--
-- Name: index_daily_price; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.index_daily_price (
    id integer NOT NULL,
    index_code character varying(10) NOT NULL,
    index_name character varying(50),
    date date NOT NULL,
    open double precision,
    high double precision,
    low double precision,
    close double precision NOT NULL,
    volume bigint,
    trading_value bigint,
    change double precision,
    change_rate double precision,
    change_sign character varying(1),
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.index_daily_price OWNER TO postgres;

--
-- Name: TABLE index_daily_price; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.index_daily_price IS '업종/지수 일자별 데이터 (KIS API, 매일 18:00 수집)';


--
-- Name: COLUMN index_daily_price.id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.index_daily_price.id IS 'Primary key';


--
-- Name: COLUMN index_daily_price.index_code; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.index_daily_price.index_code IS '지수 코드 (0001:KOSPI, 1001:KOSDAQ, 2001:KOSPI200 등)';


--
-- Name: COLUMN index_daily_price.index_name; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.index_daily_price.index_name IS '지수명 (KOSPI, KOSDAQ, 에너지, 화학 등)';


--
-- Name: COLUMN index_daily_price.date; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.index_daily_price.date IS '영업일자';


--
-- Name: COLUMN index_daily_price.open; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.index_daily_price.open IS '시가';


--
-- Name: COLUMN index_daily_price.high; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.index_daily_price.high IS '최고가';


--
-- Name: COLUMN index_daily_price.low; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.index_daily_price.low IS '최저가';


--
-- Name: COLUMN index_daily_price.close; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.index_daily_price.close IS '종가';


--
-- Name: COLUMN index_daily_price.volume; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.index_daily_price.volume IS '누적 거래량';


--
-- Name: COLUMN index_daily_price.trading_value; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.index_daily_price.trading_value IS '누적 거래대금';


--
-- Name: COLUMN index_daily_price.change; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.index_daily_price.change IS '전일 대비';


--
-- Name: COLUMN index_daily_price.change_rate; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.index_daily_price.change_rate IS '전일 대비율 (%)';


--
-- Name: COLUMN index_daily_price.change_sign; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.index_daily_price.change_sign IS '전일 대비 부호 (1:상한, 2:상승, 3:보합, 4:하한, 5:하락)';


--
-- Name: COLUMN index_daily_price.created_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.index_daily_price.created_at IS '생성일시';


--
-- Name: index_daily_price_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.index_daily_price_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.index_daily_price_id_seq OWNER TO postgres;

--
-- Name: index_daily_price_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.index_daily_price_id_seq OWNED BY public.index_daily_price.id;


--
-- Name: investor_trading; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.investor_trading (
    id integer NOT NULL,
    stock_code character varying(10) NOT NULL,
    date timestamp without time zone NOT NULL,
    stck_clpr double precision,
    prsn_ntby_qty bigint,
    frgn_ntby_qty bigint,
    orgn_ntby_qty bigint,
    prsn_ntby_tr_pbmn bigint,
    frgn_ntby_tr_pbmn bigint,
    orgn_ntby_tr_pbmn bigint,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.investor_trading OWNER TO postgres;

--
-- Name: TABLE investor_trading; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.investor_trading IS '투자자별 매매동향 (매일 16:00 수집)';


--
-- Name: COLUMN investor_trading.id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.investor_trading.id IS 'Primary Key';


--
-- Name: COLUMN investor_trading.stock_code; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.investor_trading.stock_code IS '종목코드';


--
-- Name: COLUMN investor_trading.date; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.investor_trading.date IS '거래일';


--
-- Name: COLUMN investor_trading.stck_clpr; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.investor_trading.stck_clpr IS '주식 종가';


--
-- Name: COLUMN investor_trading.prsn_ntby_qty; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.investor_trading.prsn_ntby_qty IS '개인 순매수 수량';


--
-- Name: COLUMN investor_trading.frgn_ntby_qty; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.investor_trading.frgn_ntby_qty IS '외국인 순매수 수량';


--
-- Name: COLUMN investor_trading.orgn_ntby_qty; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.investor_trading.orgn_ntby_qty IS '기관계 순매수 수량';


--
-- Name: COLUMN investor_trading.prsn_ntby_tr_pbmn; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.investor_trading.prsn_ntby_tr_pbmn IS '개인 순매수 거래대금';


--
-- Name: COLUMN investor_trading.frgn_ntby_tr_pbmn; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.investor_trading.frgn_ntby_tr_pbmn IS '외국인 순매수 거래대금';


--
-- Name: COLUMN investor_trading.orgn_ntby_tr_pbmn; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.investor_trading.orgn_ntby_tr_pbmn IS '기관계 순매수 거래대금';


--
-- Name: COLUMN investor_trading.created_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.investor_trading.created_at IS '생성일시';


--
-- Name: investor_trading_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.investor_trading_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.investor_trading_id_seq OWNER TO postgres;

--
-- Name: investor_trading_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.investor_trading_id_seq OWNED BY public.investor_trading.id;


--
-- Name: model_evaluations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.model_evaluations (
    id integer NOT NULL,
    prediction_id integer NOT NULL,
    model_id integer NOT NULL,
    stock_code character varying(10) NOT NULL,
    predicted_at timestamp without time zone NOT NULL,
    prediction_period character varying(20),
    predicted_target_price double precision,
    predicted_support_price double precision,
    predicted_base_price double precision NOT NULL,
    predicted_confidence double precision,
    actual_high_1d double precision,
    actual_low_1d double precision,
    actual_close_1d double precision,
    actual_high_5d double precision,
    actual_low_5d double precision,
    actual_close_5d double precision,
    target_achieved boolean,
    target_achieved_days integer,
    support_breached boolean,
    target_accuracy_score double precision,
    timing_score double precision,
    risk_management_score double precision,
    human_rating_quality integer,
    human_rating_usefulness integer,
    human_rating_overall integer,
    human_evaluated_by character varying(50),
    human_evaluated_at timestamp without time zone,
    final_score double precision,
    evaluated_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.model_evaluations OWNER TO postgres;

--
-- Name: model_evaluations_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.model_evaluations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.model_evaluations_id_seq OWNER TO postgres;

--
-- Name: model_evaluations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.model_evaluations_id_seq OWNED BY public.model_evaluations.id;


--
-- Name: models; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.models (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    provider character varying(50) NOT NULL,
    model_identifier character varying(200) NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    description character varying(500),
    created_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.models OWNER TO postgres;

--
-- Name: models_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.models_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.models_id_seq OWNER TO postgres;

--
-- Name: models_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.models_id_seq OWNED BY public.models.id;


--
-- Name: news_articles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.news_articles (
    id integer NOT NULL,
    title character varying(500) NOT NULL,
    content text NOT NULL,
    published_at timestamp without time zone NOT NULL,
    source character varying(100) NOT NULL,
    stock_code character varying(10),
    created_at timestamp without time zone NOT NULL,
    notified_at timestamp without time zone,
    content_type public.contenttype DEFAULT 'news'::public.contenttype NOT NULL,
    url character varying(1000),
    author character varying(200),
    upvotes integer,
    num_comments integer,
    subreddit character varying(100),
    metadata jsonb
);


ALTER TABLE public.news_articles OWNER TO postgres;

--
-- Name: TABLE news_articles; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.news_articles IS '뉴스 기사 (10분마다 크롤링)';


--
-- Name: COLUMN news_articles.id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.news_articles.id IS 'Primary Key';


--
-- Name: COLUMN news_articles.title; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.news_articles.title IS '기사 제목';


--
-- Name: COLUMN news_articles.content; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.news_articles.content IS '기사 본문';


--
-- Name: COLUMN news_articles.published_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.news_articles.published_at IS '발행 시간';


--
-- Name: COLUMN news_articles.source; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.news_articles.source IS '출처 (네이버, DART 등)';


--
-- Name: COLUMN news_articles.stock_code; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.news_articles.stock_code IS '관련 종목코드';


--
-- Name: COLUMN news_articles.created_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.news_articles.created_at IS '생성일시';


--
-- Name: COLUMN news_articles.notified_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.news_articles.notified_at IS '텔레그램 알림 발송 시간';


--
-- Name: COLUMN news_articles.url; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.news_articles.url IS '기사 URL';


--
-- Name: news_articles_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.news_articles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.news_articles_id_seq OWNER TO postgres;

--
-- Name: news_articles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.news_articles_id_seq OWNED BY public.news_articles.id;


--
-- Name: news_stock_matches; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.news_stock_matches (
    id integer NOT NULL,
    news_id integer NOT NULL,
    stock_code character varying(10) NOT NULL,
    price_change_1d double precision,
    price_change_3d double precision,
    price_change_5d double precision,
    calculated_at timestamp without time zone NOT NULL,
    price_change_2d double precision,
    price_change_10d double precision,
    price_change_20d double precision
);


ALTER TABLE public.news_stock_matches OWNER TO postgres;

--
-- Name: news_stock_matches_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.news_stock_matches_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.news_stock_matches_id_seq OWNER TO postgres;

--
-- Name: news_stock_matches_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.news_stock_matches_id_seq OWNED BY public.news_stock_matches.id;


--
-- Name: predictions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.predictions (
    id integer NOT NULL,
    news_id integer NOT NULL,
    stock_code character varying(10) NOT NULL,
    direction character varying(10),
    confidence double precision,
    reasoning text,
    current_price double precision,
    target_period character varying(20) NOT NULL,
    created_at timestamp without time zone NOT NULL,
    short_term text,
    medium_term text,
    long_term text,
    confidence_breakdown json,
    pattern_analysis json,
    model_id integer,
    sentiment_direction character varying(10),
    sentiment_score double precision,
    impact_level character varying(20),
    relevance_score double precision,
    urgency_level character varying(20),
    impact_analysis json
);


ALTER TABLE public.predictions OWNER TO postgres;

--
-- Name: TABLE predictions; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.predictions IS 'AI 뉴스 영향도 예측 결과';


--
-- Name: COLUMN predictions.id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.predictions.id IS 'Primary Key';


--
-- Name: COLUMN predictions.news_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.predictions.news_id IS '뉴스 ID (news_articles 참조)';


--
-- Name: COLUMN predictions.stock_code; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.predictions.stock_code IS '종목코드';


--
-- Name: COLUMN predictions.reasoning; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.predictions.reasoning IS 'AI 추론 근거';


--
-- Name: COLUMN predictions.created_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.predictions.created_at IS '생성일시';


--
-- Name: COLUMN predictions.sentiment_direction; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.predictions.sentiment_direction IS '감성 방향 (positive/negative/neutral)';


--
-- Name: COLUMN predictions.sentiment_score; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.predictions.sentiment_score IS '감성 점수 (-1.0 ~ 1.0)';


--
-- Name: COLUMN predictions.impact_level; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.predictions.impact_level IS '영향 수준 (high/medium/low)';


--
-- Name: COLUMN predictions.relevance_score; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.predictions.relevance_score IS '관련성 점수 (0.0 ~ 1.0)';


--
-- Name: COLUMN predictions.urgency_level; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.predictions.urgency_level IS '긴급도 (urgent/notable/routine)';


--
-- Name: COLUMN predictions.impact_analysis; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.predictions.impact_analysis IS '영향 분석 JSON';


--
-- Name: predictions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.predictions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.predictions_id_seq OWNER TO postgres;

--
-- Name: predictions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.predictions_id_seq OWNED BY public.predictions.id;


--
-- Name: sector_index; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.sector_index (
    id integer NOT NULL,
    sector_code character varying(10) NOT NULL,
    datetime timestamp without time zone NOT NULL,
    bstp_nmix_prpr double precision,
    bstp_nmix_prdy_vrss double precision,
    bstp_nmix_prdy_ctrt double precision,
    acml_vol bigint,
    acml_tr_pbmn bigint,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.sector_index OWNER TO postgres;

--
-- Name: TABLE sector_index; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.sector_index IS '업종 지수 (장중 5분마다 수집)';


--
-- Name: COLUMN sector_index.id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.sector_index.id IS 'Primary Key';


--
-- Name: COLUMN sector_index.sector_code; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.sector_index.sector_code IS '업종코드 (0001:KOSPI, 1001:KOSDAQ)';


--
-- Name: COLUMN sector_index.datetime; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.sector_index.datetime IS '지수 시간';


--
-- Name: COLUMN sector_index.bstp_nmix_prpr; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.sector_index.bstp_nmix_prpr IS '업종 현재지수';


--
-- Name: COLUMN sector_index.bstp_nmix_prdy_vrss; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.sector_index.bstp_nmix_prdy_vrss IS '전일 대비';


--
-- Name: COLUMN sector_index.bstp_nmix_prdy_ctrt; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.sector_index.bstp_nmix_prdy_ctrt IS '전일 대비율 (%)';


--
-- Name: COLUMN sector_index.acml_vol; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.sector_index.acml_vol IS '누적 거래량';


--
-- Name: COLUMN sector_index.acml_tr_pbmn; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.sector_index.acml_tr_pbmn IS '누적 거래대금';


--
-- Name: COLUMN sector_index.created_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.sector_index.created_at IS '생성일시';


--
-- Name: sector_index_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.sector_index_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.sector_index_id_seq OWNER TO postgres;

--
-- Name: sector_index_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.sector_index_id_seq OWNED BY public.sector_index.id;


--
-- Name: stock_analysis_summaries; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.stock_analysis_summaries (
    id integer NOT NULL,
    stock_code character varying(10) NOT NULL,
    overall_summary text,
    short_term_scenario text,
    medium_term_scenario text,
    long_term_scenario text,
    risk_factors json,
    opportunity_factors json,
    recommendation text,
    total_predictions integer,
    up_count integer,
    down_count integer,
    hold_count integer,
    avg_confidence double precision,
    last_updated timestamp without time zone NOT NULL,
    based_on_prediction_count integer,
    custom_data json,
    model_id integer,
    short_term_target_price double precision,
    short_term_support_price double precision,
    medium_term_target_price double precision,
    medium_term_support_price double precision,
    long_term_target_price double precision,
    base_price double precision
);


ALTER TABLE public.stock_analysis_summaries OWNER TO postgres;

--
-- Name: stock_analysis_summaries_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.stock_analysis_summaries_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.stock_analysis_summaries_id_seq OWNER TO postgres;

--
-- Name: stock_analysis_summaries_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.stock_analysis_summaries_id_seq OWNED BY public.stock_analysis_summaries.id;


--
-- Name: stock_current_price; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.stock_current_price (
    id integer NOT NULL,
    stock_code character varying(10) NOT NULL,
    datetime timestamp without time zone NOT NULL,
    stck_prpr double precision,
    prdy_vrss double precision,
    prdy_vrss_sign character varying(1),
    prdy_ctrt double precision,
    acml_vol bigint,
    acml_tr_pbmn bigint,
    per double precision,
    pbr double precision,
    eps double precision,
    bps double precision,
    hts_avls bigint,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.stock_current_price OWNER TO postgres;

--
-- Name: TABLE stock_current_price; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.stock_current_price IS '실시간 현재가 시세 (장중 5분마다 수집)';


--
-- Name: COLUMN stock_current_price.id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_current_price.id IS 'Primary Key';


--
-- Name: COLUMN stock_current_price.stock_code; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_current_price.stock_code IS '종목코드';


--
-- Name: COLUMN stock_current_price.datetime; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_current_price.datetime IS '시세 시간';


--
-- Name: COLUMN stock_current_price.stck_prpr; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_current_price.stck_prpr IS '주식 현재가';


--
-- Name: COLUMN stock_current_price.prdy_vrss; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_current_price.prdy_vrss IS '전일 대비';


--
-- Name: COLUMN stock_current_price.prdy_vrss_sign; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_current_price.prdy_vrss_sign IS '전일 대비 부호 (2:상승, 5:하락, 3:보합)';


--
-- Name: COLUMN stock_current_price.prdy_ctrt; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_current_price.prdy_ctrt IS '전일 대비율 (%)';


--
-- Name: COLUMN stock_current_price.acml_vol; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_current_price.acml_vol IS '누적 거래량';


--
-- Name: COLUMN stock_current_price.acml_tr_pbmn; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_current_price.acml_tr_pbmn IS '누적 거래대금';


--
-- Name: COLUMN stock_current_price.per; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_current_price.per IS 'PER (주가수익비율)';


--
-- Name: COLUMN stock_current_price.pbr; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_current_price.pbr IS 'PBR (주가순자산비율)';


--
-- Name: COLUMN stock_current_price.eps; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_current_price.eps IS 'EPS (주당순이익)';


--
-- Name: COLUMN stock_current_price.bps; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_current_price.bps IS 'BPS (주당순자산가치)';


--
-- Name: COLUMN stock_current_price.hts_avls; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_current_price.hts_avls IS 'HTS 시가총액';


--
-- Name: COLUMN stock_current_price.created_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_current_price.created_at IS '생성일시';


--
-- Name: stock_current_price_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.stock_current_price_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.stock_current_price_id_seq OWNER TO postgres;

--
-- Name: stock_current_price_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.stock_current_price_id_seq OWNED BY public.stock_current_price.id;


--
-- Name: stock_info; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.stock_info (
    id integer NOT NULL,
    stock_code character varying(10) NOT NULL,
    std_idst_clsf_cd character varying(10),
    std_idst_clsf_cd_name character varying(100),
    hts_avls bigint,
    lstn_stcn bigint,
    cpfn bigint,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.stock_info OWNER TO postgres;

--
-- Name: TABLE stock_info; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.stock_info IS '종목 기본정보 (KIS API, 매일 16:10 수집)';


--
-- Name: COLUMN stock_info.id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_info.id IS 'Primary Key';


--
-- Name: COLUMN stock_info.stock_code; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_info.stock_code IS '종목코드';


--
-- Name: COLUMN stock_info.std_idst_clsf_cd; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_info.std_idst_clsf_cd IS '표준산업분류코드';


--
-- Name: COLUMN stock_info.std_idst_clsf_cd_name; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_info.std_idst_clsf_cd_name IS '업종명';


--
-- Name: COLUMN stock_info.hts_avls; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_info.hts_avls IS '시가총액';


--
-- Name: COLUMN stock_info.lstn_stcn; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_info.lstn_stcn IS '상장주식수';


--
-- Name: COLUMN stock_info.cpfn; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_info.cpfn IS '자본금';


--
-- Name: COLUMN stock_info.updated_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_info.updated_at IS '최종 업데이트 시간';


--
-- Name: stock_info_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.stock_info_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.stock_info_id_seq OWNER TO postgres;

--
-- Name: stock_info_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.stock_info_id_seq OWNED BY public.stock_info.id;


--
-- Name: stock_orderbook; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.stock_orderbook (
    id integer NOT NULL,
    stock_code character varying(10) NOT NULL,
    datetime timestamp without time zone NOT NULL,
    askp1 double precision,
    askp2 double precision,
    askp3 double precision,
    askp4 double precision,
    askp5 double precision,
    askp6 double precision,
    askp7 double precision,
    askp8 double precision,
    askp9 double precision,
    askp10 double precision,
    askp_rsqn1 bigint,
    askp_rsqn2 bigint,
    askp_rsqn3 bigint,
    askp_rsqn4 bigint,
    askp_rsqn5 bigint,
    askp_rsqn6 bigint,
    askp_rsqn7 bigint,
    askp_rsqn8 bigint,
    askp_rsqn9 bigint,
    askp_rsqn10 bigint,
    bidp1 double precision,
    bidp2 double precision,
    bidp3 double precision,
    bidp4 double precision,
    bidp5 double precision,
    bidp6 double precision,
    bidp7 double precision,
    bidp8 double precision,
    bidp9 double precision,
    bidp10 double precision,
    bidp_rsqn1 bigint,
    bidp_rsqn2 bigint,
    bidp_rsqn3 bigint,
    bidp_rsqn4 bigint,
    bidp_rsqn5 bigint,
    bidp_rsqn6 bigint,
    bidp_rsqn7 bigint,
    bidp_rsqn8 bigint,
    bidp_rsqn9 bigint,
    bidp_rsqn10 bigint,
    total_askp_rsqn bigint,
    total_bidp_rsqn bigint,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.stock_orderbook OWNER TO postgres;

--
-- Name: TABLE stock_orderbook; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.stock_orderbook IS '호가 데이터 (10단계 매수/매도, 장중 5분마다 수집)';


--
-- Name: COLUMN stock_orderbook.id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_orderbook.id IS 'Primary Key';


--
-- Name: COLUMN stock_orderbook.stock_code; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_orderbook.stock_code IS '종목코드';


--
-- Name: COLUMN stock_orderbook.datetime; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_orderbook.datetime IS '호가 시간';


--
-- Name: COLUMN stock_orderbook.askp1; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_orderbook.askp1 IS '매도 1호가';


--
-- Name: COLUMN stock_orderbook.askp2; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_orderbook.askp2 IS '매도 2호가';


--
-- Name: COLUMN stock_orderbook.askp3; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_orderbook.askp3 IS '매도 3호가';


--
-- Name: COLUMN stock_orderbook.askp4; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_orderbook.askp4 IS '매도 4호가';


--
-- Name: COLUMN stock_orderbook.askp5; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_orderbook.askp5 IS '매도 5호가';


--
-- Name: COLUMN stock_orderbook.askp6; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_orderbook.askp6 IS '매도 6호가';


--
-- Name: COLUMN stock_orderbook.askp7; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_orderbook.askp7 IS '매도 7호가';


--
-- Name: COLUMN stock_orderbook.askp8; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_orderbook.askp8 IS '매도 8호가';


--
-- Name: COLUMN stock_orderbook.askp9; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_orderbook.askp9 IS '매도 9호가';


--
-- Name: COLUMN stock_orderbook.askp10; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_orderbook.askp10 IS '매도 10호가';


--
-- Name: COLUMN stock_orderbook.askp_rsqn1; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_orderbook.askp_rsqn1 IS '매도 1호가 잔량';


--
-- Name: COLUMN stock_orderbook.askp_rsqn2; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_orderbook.askp_rsqn2 IS '매도 2호가 잔량';


--
-- Name: COLUMN stock_orderbook.askp_rsqn3; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_orderbook.askp_rsqn3 IS '매도 3호가 잔량';


--
-- Name: COLUMN stock_orderbook.askp_rsqn4; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_orderbook.askp_rsqn4 IS '매도 4호가 잔량';


--
-- Name: COLUMN stock_orderbook.askp_rsqn5; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_orderbook.askp_rsqn5 IS '매도 5호가 잔량';


--
-- Name: COLUMN stock_orderbook.askp_rsqn6; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_orderbook.askp_rsqn6 IS '매도 6호가 잔량';


--
-- Name: COLUMN stock_orderbook.askp_rsqn7; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_orderbook.askp_rsqn7 IS '매도 7호가 잔량';


--
-- Name: COLUMN stock_orderbook.askp_rsqn8; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_orderbook.askp_rsqn8 IS '매도 8호가 잔량';


--
-- Name: COLUMN stock_orderbook.askp_rsqn9; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_orderbook.askp_rsqn9 IS '매도 9호가 잔량';


--
-- Name: COLUMN stock_orderbook.askp_rsqn10; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_orderbook.askp_rsqn10 IS '매도 10호가 잔량';


--
-- Name: COLUMN stock_orderbook.bidp1; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_orderbook.bidp1 IS '매수 1호가';


--
-- Name: COLUMN stock_orderbook.bidp2; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_orderbook.bidp2 IS '매수 2호가';


--
-- Name: COLUMN stock_orderbook.bidp3; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_orderbook.bidp3 IS '매수 3호가';


--
-- Name: COLUMN stock_orderbook.bidp4; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_orderbook.bidp4 IS '매수 4호가';


--
-- Name: COLUMN stock_orderbook.bidp5; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_orderbook.bidp5 IS '매수 5호가';


--
-- Name: COLUMN stock_orderbook.bidp6; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_orderbook.bidp6 IS '매수 6호가';


--
-- Name: COLUMN stock_orderbook.bidp7; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_orderbook.bidp7 IS '매수 7호가';


--
-- Name: COLUMN stock_orderbook.bidp8; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_orderbook.bidp8 IS '매수 8호가';


--
-- Name: COLUMN stock_orderbook.bidp9; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_orderbook.bidp9 IS '매수 9호가';


--
-- Name: COLUMN stock_orderbook.bidp10; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_orderbook.bidp10 IS '매수 10호가';


--
-- Name: COLUMN stock_orderbook.bidp_rsqn1; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_orderbook.bidp_rsqn1 IS '매수 1호가 잔량';


--
-- Name: COLUMN stock_orderbook.bidp_rsqn2; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_orderbook.bidp_rsqn2 IS '매수 2호가 잔량';


--
-- Name: COLUMN stock_orderbook.bidp_rsqn3; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_orderbook.bidp_rsqn3 IS '매수 3호가 잔량';


--
-- Name: COLUMN stock_orderbook.bidp_rsqn4; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_orderbook.bidp_rsqn4 IS '매수 4호가 잔량';


--
-- Name: COLUMN stock_orderbook.bidp_rsqn5; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_orderbook.bidp_rsqn5 IS '매수 5호가 잔량';


--
-- Name: COLUMN stock_orderbook.bidp_rsqn6; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_orderbook.bidp_rsqn6 IS '매수 6호가 잔량';


--
-- Name: COLUMN stock_orderbook.bidp_rsqn7; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_orderbook.bidp_rsqn7 IS '매수 7호가 잔량';


--
-- Name: COLUMN stock_orderbook.bidp_rsqn8; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_orderbook.bidp_rsqn8 IS '매수 8호가 잔량';


--
-- Name: COLUMN stock_orderbook.bidp_rsqn9; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_orderbook.bidp_rsqn9 IS '매수 9호가 잔량';


--
-- Name: COLUMN stock_orderbook.bidp_rsqn10; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_orderbook.bidp_rsqn10 IS '매수 10호가 잔량';


--
-- Name: COLUMN stock_orderbook.total_askp_rsqn; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_orderbook.total_askp_rsqn IS '총 매도 잔량';


--
-- Name: COLUMN stock_orderbook.total_bidp_rsqn; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_orderbook.total_bidp_rsqn IS '총 매수 잔량';


--
-- Name: COLUMN stock_orderbook.created_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_orderbook.created_at IS '생성일시';


--
-- Name: stock_orderbook_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.stock_orderbook_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.stock_orderbook_id_seq OWNER TO postgres;

--
-- Name: stock_orderbook_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.stock_orderbook_id_seq OWNED BY public.stock_orderbook.id;


--
-- Name: stock_overtime_price; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.stock_overtime_price (
    id integer NOT NULL,
    stock_code character varying(10) NOT NULL,
    date date NOT NULL,
    ovtm_untp_prpr double precision,
    ovtm_untp_prdy_vrss double precision,
    prdy_vrss_sign character varying(1),
    ovtm_untp_prdy_ctrt double precision,
    acml_vol bigint,
    acml_tr_pbmn bigint,
    ovtm_untp_antc_cnpr double precision,
    ovtm_untp_antc_cntg_vrss double precision,
    ovtm_untp_antc_cntg_vrss_sign character varying(1),
    ovtm_untp_antc_cntg_ctrt double precision,
    ovtm_untp_antc_vol bigint,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.stock_overtime_price OWNER TO postgres;

--
-- Name: TABLE stock_overtime_price; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.stock_overtime_price IS '시간외 거래 가격 (매일 18:00 수집, 08:30~18:00 시간외 거래)';


--
-- Name: COLUMN stock_overtime_price.id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_overtime_price.id IS 'Primary Key';


--
-- Name: COLUMN stock_overtime_price.stock_code; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_overtime_price.stock_code IS '종목코드';


--
-- Name: COLUMN stock_overtime_price.date; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_overtime_price.date IS '거래일';


--
-- Name: COLUMN stock_overtime_price.ovtm_untp_prpr; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_overtime_price.ovtm_untp_prpr IS '시간외 단일가 현재가';


--
-- Name: COLUMN stock_overtime_price.ovtm_untp_prdy_vrss; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_overtime_price.ovtm_untp_prdy_vrss IS '전일 대비';


--
-- Name: COLUMN stock_overtime_price.prdy_vrss_sign; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_overtime_price.prdy_vrss_sign IS '전일 대비 부호 (2:상승, 5:하락, 3:보합)';


--
-- Name: COLUMN stock_overtime_price.ovtm_untp_prdy_ctrt; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_overtime_price.ovtm_untp_prdy_ctrt IS '전일 대비율 (%)';


--
-- Name: COLUMN stock_overtime_price.acml_vol; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_overtime_price.acml_vol IS '누적 거래량';


--
-- Name: COLUMN stock_overtime_price.acml_tr_pbmn; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_overtime_price.acml_tr_pbmn IS '누적 거래대금';


--
-- Name: COLUMN stock_overtime_price.ovtm_untp_antc_cnpr; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_overtime_price.ovtm_untp_antc_cnpr IS '예상 체결가';


--
-- Name: COLUMN stock_overtime_price.ovtm_untp_antc_cntg_vrss; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_overtime_price.ovtm_untp_antc_cntg_vrss IS '예상 체결 대비';


--
-- Name: COLUMN stock_overtime_price.ovtm_untp_antc_cntg_vrss_sign; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_overtime_price.ovtm_untp_antc_cntg_vrss_sign IS '예상 체결 대비 부호';


--
-- Name: COLUMN stock_overtime_price.ovtm_untp_antc_cntg_ctrt; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_overtime_price.ovtm_untp_antc_cntg_ctrt IS '예상 체결 대비율 (%)';


--
-- Name: COLUMN stock_overtime_price.ovtm_untp_antc_vol; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_overtime_price.ovtm_untp_antc_vol IS '예상 거래량';


--
-- Name: COLUMN stock_overtime_price.created_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_overtime_price.created_at IS '생성일시';


--
-- Name: stock_overtime_price_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.stock_overtime_price_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.stock_overtime_price_id_seq OWNER TO postgres;

--
-- Name: stock_overtime_price_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.stock_overtime_price_id_seq OWNED BY public.stock_overtime_price.id;


--
-- Name: stock_prices; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.stock_prices (
    id integer NOT NULL,
    stock_code character varying(10) NOT NULL,
    date timestamp without time zone NOT NULL,
    open double precision NOT NULL,
    high double precision NOT NULL,
    low double precision NOT NULL,
    close double precision NOT NULL,
    volume integer,
    source character varying(10) DEFAULT 'fdr'::character varying NOT NULL
);


ALTER TABLE public.stock_prices OWNER TO postgres;

--
-- Name: TABLE stock_prices; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.stock_prices IS '일봉 주가 데이터 (Historical)';


--
-- Name: COLUMN stock_prices.id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_prices.id IS 'Primary Key';


--
-- Name: COLUMN stock_prices.stock_code; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_prices.stock_code IS '종목코드';


--
-- Name: COLUMN stock_prices.date; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_prices.date IS '거래일';


--
-- Name: COLUMN stock_prices.open; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_prices.open IS '시가';


--
-- Name: COLUMN stock_prices.high; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_prices.high IS '고가';


--
-- Name: COLUMN stock_prices.low; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_prices.low IS '저가';


--
-- Name: COLUMN stock_prices.close; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_prices.close IS '종가';


--
-- Name: COLUMN stock_prices.volume; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_prices.volume IS '거래량';


--
-- Name: COLUMN stock_prices.source; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_prices.source IS '데이터 소스 (fdr/kis)';


--
-- Name: stock_prices_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.stock_prices_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.stock_prices_id_seq OWNER TO postgres;

--
-- Name: stock_prices_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.stock_prices_id_seq OWNED BY public.stock_prices.id;


--
-- Name: stock_prices_minute; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.stock_prices_minute (
    id integer NOT NULL,
    stock_code character varying(10) NOT NULL,
    datetime timestamp without time zone NOT NULL,
    open double precision NOT NULL,
    high double precision NOT NULL,
    low double precision NOT NULL,
    close double precision NOT NULL,
    volume bigint,
    source character varying(20) DEFAULT 'kis'::character varying,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.stock_prices_minute OWNER TO postgres;

--
-- Name: TABLE stock_prices_minute; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.stock_prices_minute IS '1분봉 주가 데이터 (장중 실시간 수집)';


--
-- Name: COLUMN stock_prices_minute.id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_prices_minute.id IS 'Primary Key';


--
-- Name: COLUMN stock_prices_minute.stock_code; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_prices_minute.stock_code IS '종목코드';


--
-- Name: COLUMN stock_prices_minute.datetime; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_prices_minute.datetime IS '1분봉 시간';


--
-- Name: COLUMN stock_prices_minute.open; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_prices_minute.open IS '시가';


--
-- Name: COLUMN stock_prices_minute.high; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_prices_minute.high IS '고가';


--
-- Name: COLUMN stock_prices_minute.low; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_prices_minute.low IS '저가';


--
-- Name: COLUMN stock_prices_minute.close; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_prices_minute.close IS '종가';


--
-- Name: COLUMN stock_prices_minute.volume; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_prices_minute.volume IS '거래량';


--
-- Name: COLUMN stock_prices_minute.source; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_prices_minute.source IS '데이터 소스 (kis)';


--
-- Name: COLUMN stock_prices_minute.created_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stock_prices_minute.created_at IS '생성일시';


--
-- Name: stock_prices_minute_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.stock_prices_minute_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.stock_prices_minute_id_seq OWNER TO postgres;

--
-- Name: stock_prices_minute_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.stock_prices_minute_id_seq OWNED BY public.stock_prices_minute.id;


--
-- Name: stocks; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.stocks (
    id integer NOT NULL,
    code character varying(10) NOT NULL,
    name character varying(100) NOT NULL,
    priority integer NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    market_cap bigint,
    sector character varying(100),
    per double precision,
    pbr double precision
);


ALTER TABLE public.stocks OWNER TO postgres;

--
-- Name: TABLE stocks; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.stocks IS '종목 마스터 테이블 (앱 내부 관리용)';


--
-- Name: COLUMN stocks.id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stocks.id IS 'Primary Key';


--
-- Name: COLUMN stocks.code; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stocks.code IS '종목코드 (예: 005930)';


--
-- Name: COLUMN stocks.name; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stocks.name IS '종목명 (예: 삼성전자)';


--
-- Name: COLUMN stocks.priority; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stocks.priority IS '크롤링 우선순위 (1~5, 낮을수록 우선)';


--
-- Name: COLUMN stocks.is_active; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stocks.is_active IS '활성화 여부';


--
-- Name: COLUMN stocks.created_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stocks.created_at IS '생성일시';


--
-- Name: COLUMN stocks.updated_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stocks.updated_at IS '수정일시';


--
-- Name: COLUMN stocks.market_cap; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stocks.market_cap IS '시가총액 (사용안함, stock_info 사용)';


--
-- Name: COLUMN stocks.sector; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stocks.sector IS '업종 (사용안함, stock_info 사용)';


--
-- Name: COLUMN stocks.per; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stocks.per IS 'PER (사용안함)';


--
-- Name: COLUMN stocks.pbr; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.stocks.pbr IS 'PBR (사용안함)';


--
-- Name: stocks_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.stocks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.stocks_id_seq OWNER TO postgres;

--
-- Name: stocks_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.stocks_id_seq OWNED BY public.stocks.id;


--
-- Name: telegram_users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.telegram_users (
    id integer NOT NULL,
    user_id character varying(50) NOT NULL,
    subscribed_at timestamp without time zone NOT NULL,
    is_active boolean NOT NULL
);


ALTER TABLE public.telegram_users OWNER TO postgres;

--
-- Name: telegram_users_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.telegram_users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.telegram_users_id_seq OWNER TO postgres;

--
-- Name: telegram_users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.telegram_users_id_seq OWNED BY public.telegram_users.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id integer NOT NULL,
    email character varying(255) NOT NULL,
    nickname character varying(100) NOT NULL,
    password_hash character varying(255) NOT NULL,
    role character varying(20) NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.users_id_seq OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: ab_test_config id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ab_test_config ALTER COLUMN id SET DEFAULT nextval('public.ab_test_config_id_seq'::regclass);


--
-- Name: daily_model_performance id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.daily_model_performance ALTER COLUMN id SET DEFAULT nextval('public.daily_model_performance_id_seq'::regclass);


--
-- Name: evaluation_history id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.evaluation_history ALTER COLUMN id SET DEFAULT nextval('public.evaluation_history_id_seq'::regclass);


--
-- Name: index_daily_price id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.index_daily_price ALTER COLUMN id SET DEFAULT nextval('public.index_daily_price_id_seq'::regclass);


--
-- Name: investor_trading id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.investor_trading ALTER COLUMN id SET DEFAULT nextval('public.investor_trading_id_seq'::regclass);


--
-- Name: model_evaluations id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.model_evaluations ALTER COLUMN id SET DEFAULT nextval('public.model_evaluations_id_seq'::regclass);


--
-- Name: models id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.models ALTER COLUMN id SET DEFAULT nextval('public.models_id_seq'::regclass);


--
-- Name: news_articles id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.news_articles ALTER COLUMN id SET DEFAULT nextval('public.news_articles_id_seq'::regclass);


--
-- Name: news_stock_matches id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.news_stock_matches ALTER COLUMN id SET DEFAULT nextval('public.news_stock_matches_id_seq'::regclass);


--
-- Name: predictions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.predictions ALTER COLUMN id SET DEFAULT nextval('public.predictions_id_seq'::regclass);


--
-- Name: sector_index id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sector_index ALTER COLUMN id SET DEFAULT nextval('public.sector_index_id_seq'::regclass);


--
-- Name: stock_analysis_summaries id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stock_analysis_summaries ALTER COLUMN id SET DEFAULT nextval('public.stock_analysis_summaries_id_seq'::regclass);


--
-- Name: stock_current_price id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stock_current_price ALTER COLUMN id SET DEFAULT nextval('public.stock_current_price_id_seq'::regclass);


--
-- Name: stock_info id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stock_info ALTER COLUMN id SET DEFAULT nextval('public.stock_info_id_seq'::regclass);


--
-- Name: stock_orderbook id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stock_orderbook ALTER COLUMN id SET DEFAULT nextval('public.stock_orderbook_id_seq'::regclass);


--
-- Name: stock_overtime_price id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stock_overtime_price ALTER COLUMN id SET DEFAULT nextval('public.stock_overtime_price_id_seq'::regclass);


--
-- Name: stock_prices id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stock_prices ALTER COLUMN id SET DEFAULT nextval('public.stock_prices_id_seq'::regclass);


--
-- Name: stock_prices_minute id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stock_prices_minute ALTER COLUMN id SET DEFAULT nextval('public.stock_prices_minute_id_seq'::regclass);


--
-- Name: stocks id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stocks ALTER COLUMN id SET DEFAULT nextval('public.stocks_id_seq'::regclass);


--
-- Name: telegram_users id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.telegram_users ALTER COLUMN id SET DEFAULT nextval('public.telegram_users_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: ab_test_config ab_test_config_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ab_test_config
    ADD CONSTRAINT ab_test_config_pkey PRIMARY KEY (id);


--
-- Name: daily_model_performance daily_model_performance_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.daily_model_performance
    ADD CONSTRAINT daily_model_performance_pkey PRIMARY KEY (id);


--
-- Name: evaluation_history evaluation_history_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.evaluation_history
    ADD CONSTRAINT evaluation_history_pkey PRIMARY KEY (id);


--
-- Name: index_daily_price index_daily_price_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.index_daily_price
    ADD CONSTRAINT index_daily_price_pkey PRIMARY KEY (id);


--
-- Name: investor_trading investor_trading_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.investor_trading
    ADD CONSTRAINT investor_trading_pkey PRIMARY KEY (id);


--
-- Name: model_evaluations model_evaluations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.model_evaluations
    ADD CONSTRAINT model_evaluations_pkey PRIMARY KEY (id);


--
-- Name: models models_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.models
    ADD CONSTRAINT models_name_key UNIQUE (name);


--
-- Name: models models_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.models
    ADD CONSTRAINT models_pkey PRIMARY KEY (id);


--
-- Name: news_articles news_articles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.news_articles
    ADD CONSTRAINT news_articles_pkey PRIMARY KEY (id);


--
-- Name: news_stock_matches news_stock_matches_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.news_stock_matches
    ADD CONSTRAINT news_stock_matches_pkey PRIMARY KEY (id);


--
-- Name: predictions predictions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.predictions
    ADD CONSTRAINT predictions_pkey PRIMARY KEY (id);


--
-- Name: sector_index sector_index_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sector_index
    ADD CONSTRAINT sector_index_pkey PRIMARY KEY (id);


--
-- Name: stock_analysis_summaries stock_analysis_summaries_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stock_analysis_summaries
    ADD CONSTRAINT stock_analysis_summaries_pkey PRIMARY KEY (id);


--
-- Name: stock_current_price stock_current_price_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stock_current_price
    ADD CONSTRAINT stock_current_price_pkey PRIMARY KEY (id);


--
-- Name: stock_info stock_info_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stock_info
    ADD CONSTRAINT stock_info_pkey PRIMARY KEY (id);


--
-- Name: stock_orderbook stock_orderbook_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stock_orderbook
    ADD CONSTRAINT stock_orderbook_pkey PRIMARY KEY (id);


--
-- Name: stock_overtime_price stock_overtime_price_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stock_overtime_price
    ADD CONSTRAINT stock_overtime_price_pkey PRIMARY KEY (id);


--
-- Name: stock_prices_minute stock_prices_minute_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stock_prices_minute
    ADD CONSTRAINT stock_prices_minute_pkey PRIMARY KEY (id);


--
-- Name: stock_prices stock_prices_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stock_prices
    ADD CONSTRAINT stock_prices_pkey PRIMARY KEY (id);


--
-- Name: stocks stocks_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stocks
    ADD CONSTRAINT stocks_pkey PRIMARY KEY (id);


--
-- Name: telegram_users telegram_users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.telegram_users
    ADD CONSTRAINT telegram_users_pkey PRIMARY KEY (id);


--
-- Name: telegram_users telegram_users_user_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.telegram_users
    ADD CONSTRAINT telegram_users_user_id_key UNIQUE (user_id);


--
-- Name: index_daily_price uk_index_daily_code_date; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.index_daily_price
    ADD CONSTRAINT uk_index_daily_code_date UNIQUE (index_code, date);


--
-- Name: stock_overtime_price uk_overtime_price_stock_date; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stock_overtime_price
    ADD CONSTRAINT uk_overtime_price_stock_date UNIQUE (stock_code, date);


--
-- Name: stock_prices_minute uk_stock_datetime; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stock_prices_minute
    ADD CONSTRAINT uk_stock_datetime UNIQUE (stock_code, datetime);


--
-- Name: daily_model_performance uq_model_date; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.daily_model_performance
    ADD CONSTRAINT uq_model_date UNIQUE (model_id, date);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: idx_current_price_stock_datetime; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_current_price_stock_datetime ON public.stock_current_price USING btree (stock_code, datetime);


--
-- Name: idx_index_daily_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_index_daily_code ON public.index_daily_price USING btree (index_code);


--
-- Name: idx_index_daily_code_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_index_daily_code_date ON public.index_daily_price USING btree (index_code, date DESC);


--
-- Name: idx_index_daily_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_index_daily_date ON public.index_daily_price USING btree (date DESC);


--
-- Name: idx_investor_trading_stock_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_investor_trading_stock_date ON public.investor_trading USING btree (stock_code, date);


--
-- Name: idx_minute_datetime; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_minute_datetime ON public.stock_prices_minute USING btree (datetime DESC);


--
-- Name: idx_minute_source; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_minute_source ON public.stock_prices_minute USING btree (source);


--
-- Name: idx_minute_stock_datetime; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_minute_stock_datetime ON public.stock_prices_minute USING btree (stock_code, datetime DESC);


--
-- Name: idx_news_articles_content_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_news_articles_content_type ON public.news_articles USING btree (content_type);


--
-- Name: idx_news_articles_source_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_news_articles_source_type ON public.news_articles USING btree (source, content_type);


--
-- Name: idx_news_articles_stock_code_published_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_news_articles_stock_code_published_at ON public.news_articles USING btree (stock_code, published_at);


--
-- Name: idx_news_articles_subreddit; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_news_articles_subreddit ON public.news_articles USING btree (subreddit);


--
-- Name: idx_orderbook_stock_datetime; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_orderbook_stock_datetime ON public.stock_orderbook USING btree (stock_code, datetime);


--
-- Name: idx_overtime_price_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_overtime_price_date ON public.stock_overtime_price USING btree (date DESC);


--
-- Name: idx_overtime_price_stock_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_overtime_price_stock_code ON public.stock_overtime_price USING btree (stock_code);


--
-- Name: idx_overtime_price_stock_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_overtime_price_stock_date ON public.stock_overtime_price USING btree (stock_code, date DESC);


--
-- Name: idx_predictions_news_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_predictions_news_id ON public.predictions USING btree (news_id);


--
-- Name: idx_predictions_stock_code_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_predictions_stock_code_created ON public.predictions USING btree (stock_code, created_at);


--
-- Name: idx_sector_index_code_datetime; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_sector_index_code_datetime ON public.sector_index USING btree (sector_code, datetime);


--
-- Name: idx_stock_analysis_stock_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_stock_analysis_stock_code ON public.stock_analysis_summaries USING btree (stock_code);


--
-- Name: idx_stock_analysis_stock_code_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_stock_analysis_stock_code_date ON public.stock_analysis_summaries USING btree (stock_code, last_updated DESC);


--
-- Name: idx_stock_prices_date_source; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_stock_prices_date_source ON public.stock_prices USING btree (date, source);


--
-- Name: idx_stock_prices_stock_code_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_stock_prices_stock_code_date ON public.stock_prices USING btree (stock_code, date);


--
-- Name: idx_users_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_users_email ON public.users USING btree (email);


--
-- Name: idx_users_role; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_users_role ON public.users USING btree (role);


--
-- Name: ix_daily_model_performance_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_daily_model_performance_date ON public.daily_model_performance USING btree (date);


--
-- Name: ix_daily_model_performance_model_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_daily_model_performance_model_id ON public.daily_model_performance USING btree (model_id);


--
-- Name: ix_eval_history_eval_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_eval_history_eval_id ON public.evaluation_history USING btree (evaluation_id);


--
-- Name: ix_investor_trading_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_investor_trading_date ON public.investor_trading USING btree (date);


--
-- Name: ix_investor_trading_stock_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_investor_trading_stock_code ON public.investor_trading USING btree (stock_code);


--
-- Name: ix_model_eval_model_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_model_eval_model_date ON public.model_evaluations USING btree (model_id, predicted_at);


--
-- Name: ix_model_eval_stock_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_model_eval_stock_date ON public.model_evaluations USING btree (stock_code, predicted_at);


--
-- Name: ix_model_evaluations_model_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_model_evaluations_model_id ON public.model_evaluations USING btree (model_id);


--
-- Name: ix_model_evaluations_prediction_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_model_evaluations_prediction_id ON public.model_evaluations USING btree (prediction_id);


--
-- Name: ix_model_evaluations_stock_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_model_evaluations_stock_code ON public.model_evaluations USING btree (stock_code);


--
-- Name: ix_predictions_stock_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_predictions_stock_code ON public.predictions USING btree (stock_code);


--
-- Name: ix_sector_index_datetime; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_sector_index_datetime ON public.sector_index USING btree (datetime);


--
-- Name: ix_sector_index_sector_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_sector_index_sector_code ON public.sector_index USING btree (sector_code);


--
-- Name: ix_stock_current_price_datetime; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_stock_current_price_datetime ON public.stock_current_price USING btree (datetime);


--
-- Name: ix_stock_current_price_stock_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_stock_current_price_stock_code ON public.stock_current_price USING btree (stock_code);


--
-- Name: ix_stock_info_stock_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_stock_info_stock_code ON public.stock_info USING btree (stock_code);


--
-- Name: ix_stock_orderbook_datetime; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_stock_orderbook_datetime ON public.stock_orderbook USING btree (datetime);


--
-- Name: ix_stock_orderbook_stock_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_stock_orderbook_stock_code ON public.stock_orderbook USING btree (stock_code);


--
-- Name: ix_stocks_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_stocks_code ON public.stocks USING btree (code);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_role; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_users_role ON public.users USING btree (role);


--
-- Name: stock_overtime_price fk_stock_overtime_price_stock_code; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stock_overtime_price
    ADD CONSTRAINT fk_stock_overtime_price_stock_code FOREIGN KEY (stock_code) REFERENCES public.stocks(code);


--
-- Name: stock_prices_minute fk_stock_prices_minute_stock_code; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stock_prices_minute
    ADD CONSTRAINT fk_stock_prices_minute_stock_code FOREIGN KEY (stock_code) REFERENCES public.stocks(code);


--
-- Name: news_stock_matches news_stock_matches_news_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.news_stock_matches
    ADD CONSTRAINT news_stock_matches_news_id_fkey FOREIGN KEY (news_id) REFERENCES public.news_articles(id);


--
-- Name: predictions predictions_news_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.predictions
    ADD CONSTRAINT predictions_news_id_fkey FOREIGN KEY (news_id) REFERENCES public.news_articles(id);


--
-- Name: stock_analysis_summaries stock_analysis_summaries_model_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stock_analysis_summaries
    ADD CONSTRAINT stock_analysis_summaries_model_id_fkey FOREIGN KEY (model_id) REFERENCES public.models(id);


--
-- PostgreSQL database dump complete
--

\unrestrict X57LTFQU4AukHGKuEqMLngmwahywIYWLf99x7CSohSxAwWmvqj9lNjOd94sPMCY

