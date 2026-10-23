--
-- PostgreSQL database dump
--

\restrict 1gZS3FZcTTfMysWek6BPmg5GEmHEaLZNgWuWX0IJjgdSiRL7SEhs3VAkvWrmj0Q

-- Dumped from database version 17.10
-- Dumped by pg_dump version 17.10

-- Started on 2026-10-17 03:23:18

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- TOC entry 6 (class 2615 OID 16435)
-- Name: users; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA users;


ALTER SCHEMA users OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 223 (class 1259 OID 16414)
-- Name: cad_project; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.cad_project (
    project_id integer NOT NULL,
    project_name character varying(100) NOT NULL,
    client_name character varying(100),
    cad_file text NOT NULL,
    upload_date timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.cad_project OWNER TO postgres;

--
-- TOC entry 222 (class 1259 OID 16413)
-- Name: cad_project_project_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.cad_project_project_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.cad_project_project_id_seq OWNER TO postgres;

--
-- TOC entry 4962 (class 0 OID 0)
-- Dependencies: 222
-- Name: cad_project_project_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.cad_project_project_id_seq OWNED BY public.cad_project.project_id;


--
-- TOC entry 221 (class 1259 OID 16398)
-- Name: furniture_style; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.furniture_style (
    style_id integer NOT NULL,
    type_id integer NOT NULL,
    style_name character varying(50) NOT NULL,
    prefab_path text NOT NULL,
    preview_image text
);


ALTER TABLE public.furniture_style OWNER TO postgres;

--
-- TOC entry 220 (class 1259 OID 16397)
-- Name: furniture_style_style_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.furniture_style_style_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.furniture_style_style_id_seq OWNER TO postgres;

--
-- TOC entry 4963 (class 0 OID 0)
-- Dependencies: 220
-- Name: furniture_style_style_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.furniture_style_style_id_seq OWNED BY public.furniture_style.style_id;


--
-- TOC entry 219 (class 1259 OID 16389)
-- Name: furniture_type; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.furniture_type (
    type_id integer NOT NULL,
    type_name character varying(50) NOT NULL
);


ALTER TABLE public.furniture_type OWNER TO postgres;

--
-- TOC entry 218 (class 1259 OID 16388)
-- Name: furniture_type_type_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.furniture_type_type_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.furniture_type_type_id_seq OWNER TO postgres;

--
-- TOC entry 4964 (class 0 OID 0)
-- Dependencies: 218
-- Name: furniture_type_type_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.furniture_type_type_id_seq OWNED BY public.furniture_type.type_id;


--
-- TOC entry 225 (class 1259 OID 16424)
-- Name: generated_room; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.generated_room (
    room_id integer NOT NULL,
    project_id integer NOT NULL,
    room_name character varying(50) NOT NULL
);


ALTER TABLE public.generated_room OWNER TO postgres;

--
-- TOC entry 224 (class 1259 OID 16423)
-- Name: generated_room_room_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.generated_room_room_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.generated_room_room_id_seq OWNER TO postgres;

--
-- TOC entry 4965 (class 0 OID 0)
-- Dependencies: 224
-- Name: generated_room_room_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.generated_room_room_id_seq OWNED BY public.generated_room.room_id;


--
-- TOC entry 229 (class 1259 OID 24628)
-- Name: projects; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.projects (
    id integer NOT NULL,
    owner_employee_id character varying(100) NOT NULL,
    project_name character varying(200) NOT NULL,
    description text,
    client_name character varying(200) NOT NULL,
    client_contact character varying(200),
    designer_name character varying(200) NOT NULL,
    site_address character varying(300),
    due_date date,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.projects OWNER TO postgres;

--
-- TOC entry 228 (class 1259 OID 24627)
-- Name: projects_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.projects_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.projects_id_seq OWNER TO postgres;

--
-- TOC entry 4966 (class 0 OID 0)
-- Dependencies: 228
-- Name: projects_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.projects_id_seq OWNED BY public.projects.id;


--
-- TOC entry 227 (class 1259 OID 16451)
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id integer NOT NULL,
    employee_id character varying(100) NOT NULL,
    password_hash text NOT NULL,
    is_admin boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.users OWNER TO postgres;

--
-- TOC entry 226 (class 1259 OID 16450)
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO postgres;

--
-- TOC entry 4967 (class 0 OID 0)
-- Dependencies: 226
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- TOC entry 4770 (class 2604 OID 16417)
-- Name: cad_project project_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.cad_project ALTER COLUMN project_id SET DEFAULT nextval('public.cad_project_project_id_seq'::regclass);


--
-- TOC entry 4769 (class 2604 OID 16401)
-- Name: furniture_style style_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.furniture_style ALTER COLUMN style_id SET DEFAULT nextval('public.furniture_style_style_id_seq'::regclass);


--
-- TOC entry 4768 (class 2604 OID 16392)
-- Name: furniture_type type_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.furniture_type ALTER COLUMN type_id SET DEFAULT nextval('public.furniture_type_type_id_seq'::regclass);


--
-- TOC entry 4772 (class 2604 OID 16427)
-- Name: generated_room room_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.generated_room ALTER COLUMN room_id SET DEFAULT nextval('public.generated_room_room_id_seq'::regclass);


--
-- TOC entry 4776 (class 2604 OID 24631)
-- Name: projects id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.projects ALTER COLUMN id SET DEFAULT nextval('public.projects_id_seq'::regclass);


--
-- TOC entry 4773 (class 2604 OID 16454)
-- Name: users id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- TOC entry 4950 (class 0 OID 16414)
-- Dependencies: 223
-- Data for Name: cad_project; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.cad_project (project_id, project_name, client_name, cad_file, upload_date) FROM stdin;
\.


--
-- TOC entry 4948 (class 0 OID 16398)
-- Dependencies: 221
-- Data for Name: furniture_style; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.furniture_style (style_id, type_id, style_name, prefab_path, preview_image) FROM stdin;
1	1	Modern	Assets/Furniture/Bed/bedsc.prefab	
2	1	Scandinavian	Assets/Furniture/Bed/Bunkbedsc.prefab	
3	2	Modern	Assets/Furniture/Sofa/Couch_Large1.prefab	
4	2	Scandinavian	Assets/Furniture/Sofa/Couch_Medium2.prefab	
5	2	Minimal	Assets/Furniture/Sofa/Couch_Small1.prefab	
6	3	Scandinavian	Assets/Furniture/chair/Sc.prefab	
8	4	Scandinavian	Assets/Furniture/Desk/sc.prefab	
9	12	Modern	Assets/Furniture/drawer/Drawer_mo.prefab	
10	12	Scandinavian	Assets/Furniture/drawer/drawersc.prefab	
11	5	Scandinavian	Assets/Furniture/table/ScanndinavianSideTable.prefab	
12	7	Modern	Assets/Furniture/sink/bathroomSinkSquare.prefab	
13	7	Scandinavian	Assets/Furniture/sink/WoodSink1KitchenCabinet1.prefab	
14	7	Minimal	Assets/Furniture/sink/SteelSink1KitchenCabinet1.prefab	
15	8	Modern	Assets/Furniture/stove/GasStove1.prefab	
16	8	Scandinavian	Assets/Furniture/stove/Kitchen_Oven_Large.prefab	
17	8	Minimal	Assets/Furniture/stove/model.prefab	
18	9	Modern	Assets/Furniture/shower/showerRound.prefab	
21	10	Modern	Assets/Furniture/toilet/Bathroom_Toilet.prefab	
22	10	Scandinavian	Assets/Furniture/toilet/SIEFRING_Toilet_LP.prefab	
23	10	Minimal	Assets/Furniture/toilet/toiletSquare.prefab	
24	11	Modern	Assets/Furniture/tv/TV.prefab	
25	11	Scandinavian	Assets/Furniture/tv/TV_01.prefab	
26	13	Modern	Assets/Furniture/lamp/FloorLamp1.prefab	
27	13	Scandinavian	Assets/Furniture/lamp/Light_Ceiling2.prefab	
28	13	Minimal	Assets/Furniture/lamp/Light_Ceiling4.prefab	
29	13	Industrial	Assets/Furniture/lamp/Light_Cube2.prefab	
\.


--
-- TOC entry 4946 (class 0 OID 16389)
-- Dependencies: 219
-- Data for Name: furniture_type; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.furniture_type (type_id, type_name) FROM stdin;
1	Bed
2	Sofa
3	Chair
4	Desk
5	Table
6	Wadrobe
7	sink
8	stove
9	shower
10	toilet
11	tv
12	drawer
13	lamp
\.


--
-- TOC entry 4952 (class 0 OID 16424)
-- Dependencies: 225
-- Data for Name: generated_room; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.generated_room (room_id, project_id, room_name) FROM stdin;
\.


--
-- TOC entry 4956 (class 0 OID 24628)
-- Dependencies: 229
-- Data for Name: projects; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.projects (id, owner_employee_id, project_name, description, client_name, client_contact, designer_name, site_address, due_date, created_at) FROM stdin;
1	heshavasani28@gmail.com	building	haha	hesha	9821922236	hesha	vile parle	2026-10-01	2026-10-13 20:45:28.712016+05:30
2	heshavasani28@gmail.com	apartment	hehe	bhoomm	heshavasani28@gmail.com	hesa	kandivali	2026-10-31	2026-10-13 20:58:53.796898+05:30
\.


--
-- TOC entry 4954 (class 0 OID 16451)
-- Dependencies: 227
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.users (id, employee_id, password_hash, is_admin, created_at) FROM stdin;
1	heshavasani28@gmail.com	$2a$10$5UEiZ3P55CeHzU6lNMhjCeobqlYnK1GJeje3pp84q18jb6wftyzui	f	2026-09-30 09:56:42.002105+05:30
2	bhoomidesai@gmail.com	$2a$10$k8xIoCCxOBpZXhT42S5tRuqxzeuMjIf3N1lFJRCqcirj3TQrHJ2w2	f	2026-10-13 14:58:28.63822+05:30
3	ak@gmail.com	$2a$10$nUSFQMnXck7LO7Jwef/s..AW.YtAN1Jatn.MLSyzMnNvngchlXqFS	f	2026-10-13 20:57:50.747358+05:30
\.


--
-- TOC entry 4968 (class 0 OID 0)
-- Dependencies: 222
-- Name: cad_project_project_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.cad_project_project_id_seq', 1, false);


--
-- TOC entry 4969 (class 0 OID 0)
-- Dependencies: 220
-- Name: furniture_style_style_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.furniture_style_style_id_seq', 29, true);


--
-- TOC entry 4970 (class 0 OID 0)
-- Dependencies: 218
-- Name: furniture_type_type_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.furniture_type_type_id_seq', 13, true);


--
-- TOC entry 4971 (class 0 OID 0)
-- Dependencies: 224
-- Name: generated_room_room_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.generated_room_room_id_seq', 1, false);


--
-- TOC entry 4972 (class 0 OID 0)
-- Dependencies: 228
-- Name: projects_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.projects_id_seq', 2, true);


--
-- TOC entry 4973 (class 0 OID 0)
-- Dependencies: 226
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.users_id_seq', 3, true);


--
-- TOC entry 4787 (class 2606 OID 16422)
-- Name: cad_project cad_project_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.cad_project
    ADD CONSTRAINT cad_project_pkey PRIMARY KEY (project_id);


--
-- TOC entry 4783 (class 2606 OID 16405)
-- Name: furniture_style furniture_style_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.furniture_style
    ADD CONSTRAINT furniture_style_pkey PRIMARY KEY (style_id);


--
-- TOC entry 4785 (class 2606 OID 16407)
-- Name: furniture_style furniture_style_type_id_style_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.furniture_style
    ADD CONSTRAINT furniture_style_type_id_style_name_key UNIQUE (type_id, style_name);


--
-- TOC entry 4779 (class 2606 OID 16394)
-- Name: furniture_type furniture_type_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.furniture_type
    ADD CONSTRAINT furniture_type_pkey PRIMARY KEY (type_id);


--
-- TOC entry 4781 (class 2606 OID 16396)
-- Name: furniture_type furniture_type_type_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.furniture_type
    ADD CONSTRAINT furniture_type_type_name_key UNIQUE (type_name);


--
-- TOC entry 4789 (class 2606 OID 16429)
-- Name: generated_room generated_room_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.generated_room
    ADD CONSTRAINT generated_room_pkey PRIMARY KEY (room_id);


--
-- TOC entry 4796 (class 2606 OID 24636)
-- Name: projects projects_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_pkey PRIMARY KEY (id);


--
-- TOC entry 4791 (class 2606 OID 16462)
-- Name: users users_employee_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_employee_id_key UNIQUE (employee_id);


--
-- TOC entry 4793 (class 2606 OID 16460)
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- TOC entry 4794 (class 1259 OID 24642)
-- Name: idx_projects_owner; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_projects_owner ON public.projects USING btree (owner_employee_id, created_at DESC);


--
-- TOC entry 4797 (class 2606 OID 16408)
-- Name: furniture_style furniture_style_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.furniture_style
    ADD CONSTRAINT furniture_style_type_id_fkey FOREIGN KEY (type_id) REFERENCES public.furniture_type(type_id) ON DELETE CASCADE;


--
-- TOC entry 4798 (class 2606 OID 16430)
-- Name: generated_room generated_room_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.generated_room
    ADD CONSTRAINT generated_room_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.cad_project(project_id) ON DELETE CASCADE;


--
-- TOC entry 4799 (class 2606 OID 24637)
-- Name: projects projects_owner_employee_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_owner_employee_id_fkey FOREIGN KEY (owner_employee_id) REFERENCES public.users(employee_id) ON DELETE CASCADE;


-- Completed on 2026-10-17 03:23:19

--
-- PostgreSQL database dump complete
--

\unrestrict 1gZS3FZcTTfMysWek6BPmg5GEmHEaLZNgWuWX0IJjgdSiRL7SEhs3VAkvWrmj0Q

