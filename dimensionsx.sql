--
-- PostgreSQL database dump
--

\restrict M88sZ8uK8qhJzrw1bBlbGTk6Kg3I8IvNxzV1U4D6Lc8gaTapbieh3gcA15BBfcN

-- Dumped from database version 17.10
-- Dumped by pg_dump version 17.10

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
-- Name: users; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA users;


ALTER SCHEMA users OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
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
-- Name: cad_project_project_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.cad_project_project_id_seq OWNED BY public.cad_project.project_id;


--
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
-- Name: furniture_style_style_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.furniture_style_style_id_seq OWNED BY public.furniture_style.style_id;


--
-- Name: furniture_type; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.furniture_type (
    type_id integer NOT NULL,
    type_name character varying(50) NOT NULL
);


ALTER TABLE public.furniture_type OWNER TO postgres;

--
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
-- Name: furniture_type_type_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.furniture_type_type_id_seq OWNED BY public.furniture_type.type_id;


--
-- Name: generated_room; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.generated_room (
    room_id integer NOT NULL,
    project_id integer NOT NULL,
    room_name character varying(50) NOT NULL
);


ALTER TABLE public.generated_room OWNER TO postgres;

--
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
-- Name: generated_room_room_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.generated_room_room_id_seq OWNED BY public.generated_room.room_id;


--
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
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: cad_project project_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.cad_project ALTER COLUMN project_id SET DEFAULT nextval('public.cad_project_project_id_seq'::regclass);


--
-- Name: furniture_style style_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.furniture_style ALTER COLUMN style_id SET DEFAULT nextval('public.furniture_style_style_id_seq'::regclass);


--
-- Name: furniture_type type_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.furniture_type ALTER COLUMN type_id SET DEFAULT nextval('public.furniture_type_type_id_seq'::regclass);


--
-- Name: generated_room room_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.generated_room ALTER COLUMN room_id SET DEFAULT nextval('public.generated_room_room_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Data for Name: cad_project; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.cad_project (project_id, project_name, client_name, cad_file, upload_date) FROM stdin;
\.


--
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
-- Data for Name: generated_room; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.generated_room (room_id, project_id, room_name) FROM stdin;
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.users (id, employee_id, password_hash, is_admin, created_at) FROM stdin;
1	heshavasani28@gmail.com	$2a$10$5UEiZ3P55CeHzU6lNMhjCeobqlYnK1GJeje3pp84q18jb6wftyzui	f	2026-09-30 09:56:42.002105+05:30
\.


--
-- Name: cad_project_project_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.cad_project_project_id_seq', 1, false);


--
-- Name: furniture_style_style_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.furniture_style_style_id_seq', 29, true);


--
-- Name: furniture_type_type_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.furniture_type_type_id_seq', 13, true);


--
-- Name: generated_room_room_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.generated_room_room_id_seq', 1, false);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.users_id_seq', 1, true);


--
-- Name: cad_project cad_project_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.cad_project
    ADD CONSTRAINT cad_project_pkey PRIMARY KEY (project_id);


--
-- Name: furniture_style furniture_style_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.furniture_style
    ADD CONSTRAINT furniture_style_pkey PRIMARY KEY (style_id);


--
-- Name: furniture_style furniture_style_type_id_style_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.furniture_style
    ADD CONSTRAINT furniture_style_type_id_style_name_key UNIQUE (type_id, style_name);


--
-- Name: furniture_type furniture_type_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.furniture_type
    ADD CONSTRAINT furniture_type_pkey PRIMARY KEY (type_id);


--
-- Name: furniture_type furniture_type_type_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.furniture_type
    ADD CONSTRAINT furniture_type_type_name_key UNIQUE (type_name);


--
-- Name: generated_room generated_room_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.generated_room
    ADD CONSTRAINT generated_room_pkey PRIMARY KEY (room_id);


--
-- Name: users users_employee_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_employee_id_key UNIQUE (employee_id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: furniture_style furniture_style_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.furniture_style
    ADD CONSTRAINT furniture_style_type_id_fkey FOREIGN KEY (type_id) REFERENCES public.furniture_type(type_id) ON DELETE CASCADE;


--
-- Name: generated_room generated_room_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.generated_room
    ADD CONSTRAINT generated_room_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.cad_project(project_id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict M88sZ8uK8qhJzrw1bBlbGTk6Kg3I8IvNxzV1U4D6Lc8gaTapbieh3gcA15BBfcN

