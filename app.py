"""Տեղային Python միջերես՝ տեսախցիկով երթևեկության հոսքի վերլուծության համար."""
import json
import re
from pathlib import Path
import subprocess
import sys
import uuid
import time
import hashlib
import signal
import cv2
import numpy as np
import pandas as pd
import streamlit as st
from traffic_cnn.flow import flow_windows
from traffic_cnn.geometry import validate_line, direction_labels as line_direction_labels
from traffic_cnn.evaluation import evaluate_run
from traffic_cnn.reference_ui import annotation_tool
from traffic_cnn.calibration import Calibration
from traffic_cnn.traffic_state import LOS_DESCRIPTION, vehicle_groups
try:
    from streamlit_image_coordinates import streamlit_image_coordinates as image_coordinates
except ImportError:  # fallback: show the frame without click support
    def image_coordinates(image, width=None, key=None):
        st.image(image, width=width)
        return None

ROOT = Path(__file__).resolve().parent
TITLE = 'Երթևեկության հոսքի վերլուծություն'
CLASS_LABELS = {'car':'Մարդատար','van':'Միկրոավտոբուս/ֆուրգոն','truck':'Բեռնատար','bus':'Ավտոբուս','motorcycle':'Մոտոցիկլ'}
PRESETS = {'vehicles.mp4':'configs/calibration-vehicles.json','vehicles-2.mp4':'configs/calibration-vehicles-2.json'}
# Counting lines of the demo videos inside their calibrated zones (same as the thesis runs);
# vehicles-2.mp4: approaching carriageway only, where the calibration rectangle lies.
LINE_PRESETS = {'vehicles.mp4':dict(line=(0,1296,3839,1296),extra=(0,1700,3839,1700)),
                'vehicles-2.mp4':dict(line=(380,860,890,860),extra=(300,960,860,960))}

st.set_page_config(page_title=TITLE,page_icon='🚗',layout='wide')
st.markdown('<style>h1 {font-size:clamp(1.5rem,3.2vw,2.5rem) !important;word-break:normal !important;overflow-wrap:normal !important}</style>',unsafe_allow_html=True)
st.title(TITLE)
if st.button('Թարմացնել արդյունքները'):
    st.rerun()
st.caption('Դիպլոմային աշխատանք · CNN (YOLOv8) տրանսպորտային միջոցների հայտնաբերման համար · ByteTrack հետագծման համար · հոմոգրաֆիա արագության և խտության գնահատման համար')
video_tab, evaluation_tab, experiment_tab, data_tab = st.tabs(['Տեսանյութի վերլուծություն','Հաշվարկի ստուգում','Ուսուցում և արդյունքներ','Տվյալներ'])


def draw_polygon(image, points, color=(255,255,0)):
    overlay = image.copy()
    thickness = max(2,image.shape[1]//640)
    cv2.polylines(overlay,[np.array(points,dtype=np.int32)],True,color,thickness)
    return overlay


def fmt(value, digits=1, suffix=''):
    return '—' if value is None else f'{value:.{digits}f}{suffix}'


def relative(path):
    try:
        return str(Path(path).relative_to(ROOT))
    except ValueError:
        return None


CORNER_NAMES = ['Հեռավոր ձախ','Հեռավոր աջ','Մոտ աջ','Մոտ ձախ']
POINT_KEYS = {'Հիմնական գիծ՝ A':('ax','ay'),'Հիմնական գիծ՝ B':('bx','by'),
              'Լրացուցիչ գիծ՝ A':('ex1','ey1'),'Լրացուցիչ գիծ՝ B':('ex2','ey2'),
              **{f'Տրամաչափում՝ {name}':(f'cal{i}x',f'cal{i}y') for i,name in enumerate(CORNER_NAMES)}}


@st.cache_resource
def process_registry():
    """Analysis subprocesses survive Streamlit reruns."""
    return {}


PROCESSES = process_registry()


def reset_points(width, height, source='', preset=None):
    """Default point positions for a new video (kept across reruns otherwise); demo videos use their preset lines."""
    if st.session_state.get('points_size') == (source,width,height):
        return
    st.session_state['points_size'] = (source,width,height)
    line = preset['line'] if preset else (0,int(height*.6),width-1,int(height*.6))
    extra = preset['extra'] if preset else (0,int(height*.8),width-1,int(height*.8))
    defaults = dict(zip(('ax','ay','bx','by'),line))|dict(zip(('ex1','ey1','ex2','ey2'),extra))
    corners = [(int(width*.4),int(height*.45)),(int(width*.6),int(height*.45)),(int(width*.9),height-1),(int(width*.1),height-1)]
    for i,(x,y) in enumerate(corners):
        defaults[f'cal{i}x'],defaults[f'cal{i}y'] = x,y
    for key,value in defaults.items():
        st.session_state[key] = value


def grab_live_frame(source, timeout=15):
    """One frame from a webcam / stream, used to place lines and calibration points."""
    from traffic_cnn.sources import resolve
    cap = cv2.VideoCapture(resolve(source))
    try:
        if not cap.isOpened():
            raise ValueError('աղբյուրը չի բացվում')
        deadline = time.time()+timeout
        while time.time() < deadline:
            ok,frame = cap.read()
            if ok and frame is not None:
                return frame
            time.sleep(0.1)
        raise ValueError('կադր չի ստացվել')
    finally:
        cap.release()


def render_running_job(running):
    job = Path(running['dir'])
    process = PROCESSES.get(running['pid'])

    @st.fragment(run_every=1.0)
    def monitor():
        finished = process is None or process.poll() is not None
        progress_path = job/'results/progress.json'
        progress = {}
        if progress_path.exists():
            try:
                progress = json.loads(progress_path.read_text())
            except ValueError:
                progress = {}
        if progress.get('live'):
            limit = progress.get('max_seconds') or 1
            st.progress(min(progress.get('seconds',0)/limit,1.0),text=f"Ուղիղ հոսք՝ {progress.get('seconds',0):.0f} / {limit:.0f} վ · կադրեր՝ {progress.get('frames',0)} · հատումներ՝ {progress.get('crossings',0)}")
        elif progress:
            total = max(progress.get('total_frames',0),progress.get('frames',0),1)
            st.progress(min(progress['frames']/total,1.0),text=f"Կադրեր՝ {progress['frames']} / {total} · հատումներ՝ {progress['crossings']}")
        else:
            st.progress(0.0,text='Մոդելի բեռնում և աղբյուրի բացում…')
        preview = job/'results/preview.jpg'
        if preview.exists():
            try:
                st.image(str(preview),caption='Ընթացիկ մշակվող կադր')
            except Exception:
                pass
        if not finished and st.button('Կանգնեցնել և պահպանել արդյունքները',key='stop-job'):
            process.send_signal(signal.SIGTERM)
        if finished:
            st.session_state.pop('running_job',None)
            PROCESSES.pop(running['pid'],None)
            if (job/'results/summary.json').exists():
                st.session_state['result_directory'] = str(job/'results')
            else:
                st.session_state['job_error'] = (job/'analysis.log').read_text(errors='replace')[-6000:] if (job/'analysis.log').exists() else 'Մշակման գործընթացը չի գտնվել։'
            st.rerun(scope='app')

    st.info('Մշակումն ընթացքի մեջ է. էջը թարմացվում է ավտոմատ։')
    monitor()


with video_tab:
    st.write('Բեռնեք հաստատուն կադրային հաճախականությամբ տեսանյութ։ Մեքենաները հաշվվում են ընտրված հատվածը հատելիս, արագությունն ու խտությունը՝ տրամաչափված ճանապարհային գոտում։')
    completed = [json.loads(p.read_text()) for p in sorted((ROOT/'reports').glob('vehicle-*.json'))]
    for r in completed:
        # Reports may store weights relative to the project root (portable copies) or with an old absolute path.
        weights_path = Path(r['best_weights'])
        if not weights_path.is_absolute():
            r['best_weights'] = str(ROOT/weights_path)
        elif not weights_path.is_file() and (ROOT/'runs/experiments'/r['name']/'weights/best.pt').is_file():
            r['best_weights'] = str(ROOT/'runs/experiments'/r['name']/'weights/best.pt')
    recommended_path = ROOT/'reports/recommended-model.json'
    recommended_name = json.loads(recommended_path.read_text()).get('name') if recommended_path.exists() else None
    # The recommended model (chosen on road-camera tests) comes first; the rest by validation mAP50-95.
    completed.sort(key=lambda r:(r['name'] != recommended_name,-r['validation']['metrics/mAP50-95(B)']))
    model_labels = {relative(r['best_weights']): (('CNN զրոյից' if r['initialization'] == 'random' else 'CNN՝ լրացուցիչ ուսուցմամբ') + ' · ' + r['name'] + (' · առաջարկվող' if r['name'] == recommended_name else ''))
                    for r in completed if relative(r['best_weights']) and Path(r['best_weights']).is_file()}
    resolution_by_model = {relative(r['best_weights']): r.get('recommended_inference_imgsz',r['imgsz']) for r in completed if relative(r['best_weights'])}
    if model_labels:
        st.caption('Առաջինը առաջարկվող մոդելն է (ընտրված ճանապարհային տեսախցիկների թեստերով), մնացածը դասավորված են ստուգողական ընտրանքի mAP50–95-ով։')
    else:
        st.info('Մոդելի ուսուցումը դեռ ավարտված չէ։ Պահպանված կշիռներն այստեղ կհայտնվեն։')
    source_kind = st.radio('Տեսանյութի աղբյուր',['Ցուցադրական տեսանյութ','Սեփական ֆայլ','Ուղիղ հոսք (տեսախցիկ / URL)'],horizontal=True)
    live_mode = source_kind.startswith('Ուղիղ')
    uploaded = st.file_uploader('Ճանապարհային տեսանյութ',type=['mp4','avi','mov','mkv']) if source_kind == 'Սեփական ֆայլ' else None
    demos = {'Մայրուղի · 21,52 վ':'vehicles.mp4','Քաղաքային արագընթաց ճանապարհ · 42,54 վ':'vehicles-2.mp4'}
    demo_name = st.selectbox('Ցուցադրական տեսանյութ',list(demos)) if source_kind == 'Ցուցադրական տեսանյութ' else next(iter(demos))
    demo = ROOT/'data/video'/demos[demo_name]
    live_url, live_seconds = None, None
    if live_mode:
        live_url = st.text_input('Տեսախցիկի համար կամ հոսքի հասցե',value='0',
                                 help='0, 1 … — համակարգչի տեսախցիկ; rtsp://… — IP տեսախցիկ; http(s)://… — HLS/MJPEG հոսք կամ YouTube հղում։').strip()
        live_seconds = st.slider('Վերլուծության տևողություն, վայրկյան',10,600,60,10)
        st.caption('Ուղիղ հոսքի դեպքում վերցվում է ամենավերջին կադրը, իսկ ժամանակը չափվում է իրական ժամացույցով։ Մշակումը կարելի է կանգնեցնել ցանկացած պահի՝ արդյունքները պահպանվում են։')
    available = (uploaded is not None) if source_kind == 'Սեփական ֆայլ' else bool(live_url) if live_mode else demo.is_file()
    if source_kind == 'Ցուցադրական տեսանյութ':
        st.caption('Աղբյուրը՝ Roboflow Supervision օրինակներ։ Ժամանակը համապատասխանում է ֆայլի տևողությանը։')
    selected = st.selectbox('Մոդել',list(model_labels),format_func=lambda path:model_labels[path]) if model_labels else None
    trained_resolution = int(resolution_by_model.get(selected,640)) if selected else 640
    image_sizes = sorted({416,640,960,1280,trained_resolution})
    inference_size = st.selectbox('CNN մուտքի չափ, պիքսել',image_sizes,index=image_sizes.index(trained_resolution),help='Ավելի մեծ մուտքը պահպանում է փոքր մեքենաների մանրամասները, բայց պահանջում է ավելի շատ ժամանակ և հիշողություն։')
    use_tiles = st.checkbox('Սալիկային (tiled) հայտնաբերում՝ փոքր մեքենաների համար',value=False,
                            help='Կադրը բաժանվում է համընկնող մասերի, յուրաքանչյուրը մշակվում է առանձին և արդյունքները միավորվում են։ Օգտակար է անօդաչու սարքի և 4K տեսանյութերի համար. VisDrone-ում mAP50-ը բարձրանում է, բայց մշակումը 3–8 անգամ դանդաղում է։')
    tile_size = st.select_slider('Սալիկի չափ, պիքսել',[512,640,800,1024,1280],value=640) if use_tiles else 0
    preview_source = demo
    if uploaded is not None:
        upload_bytes = uploaded.getvalue()
        upload_dir = ROOT/'outputs/uploads'
        upload_dir.mkdir(parents=True,exist_ok=True)
        preview_source = upload_dir/(hashlib.sha256(upload_bytes).hexdigest()+Path(uploaded.name).suffix.lower())
        if not preview_source.exists():
            preview_source.write_bytes(upload_bytes)

    source_frame = None
    if available:
        if live_mode:
            if st.session_state.get('live_frame_source') != live_url:
                st.session_state.pop('live_frame',None)
            if st.button('Միանալ և վերցնել կադր'):
                try:
                    with st.spinner('Միացում հոսքին…'):
                        source_frame = grab_live_frame(live_url)
                    st.session_state['live_frame'] = source_frame
                    st.session_state['live_frame_source'] = live_url
                except ValueError as exc:
                    st.error(f'Չհաջողվեց միանալ հոսքին՝ {exc}')
                    st.session_state.pop('live_frame',None)
            source_frame = st.session_state.get('live_frame')
            if source_frame is None:
                st.info('Սեղմեք «Միանալ և վերցնել կադր»՝ գծերն ու տրամաչափումը կադրի վրա նշելու համար։')
        else:
            preview_cap = cv2.VideoCapture(str(preview_source))
            preview_ok,frame = preview_cap.read()
            preview_cap.release()
            if preview_ok:
                source_frame = frame
            else:
                st.error('Չհաջողվեց կարդալ տեսանյութի առաջին կադրը։')

    configured_line, extra_line, calibration_data, calibration_object = None, None, None, None
    if source_frame is not None:
        height,width = source_frame.shape[:2]
        demo_file = demos[demo_name] if source_kind == 'Ցուցադրական տեսանյութ' else None
        reset_points(width,height,str(demo_file or preview_source or 'live'),LINE_PRESETS.get(demo_file))
        st.subheader('1. Հաշվման գծեր')
        extra_enabled = st.checkbox('Լրացուցիչ հաշվման գիծ',help='Երկրորդ հատույթը թույլ է տալիս համեմատել հոսքը ճանապարհի երկու կետում։')
        st.subheader('2. Տրամաչափում (արագություն, խտություն)')
        has_preset = source_kind == 'Ցուցադրական տեսանյութ' and demos[demo_name] in PRESETS
        calibration_mode = st.radio('Ճանապարհային հարթության տրամաչափում',['Առանց տրամաչափման','Պատրաստի ֆայլ','Ձեռքով (4 կետ)'],horizontal=True,index=1 if has_preset else 0)

        # --- point placement by clicking on the frame ---
        targets = ['Հիմնական գիծ՝ A','Հիմնական գիծ՝ B']
        if extra_enabled:
            targets += ['Լրացուցիչ գիծ՝ A','Լրացուցիչ գիծ՝ B']
        if calibration_mode == 'Ձեռքով (4 կետ)':
            targets += [f'Տրամաչափում՝ {name}' for name in CORNER_NAMES]
        st.markdown('**Կետերի նշում կադրի վրա.** ընտրեք կետը և սեղմեք կադրի համապատասխան տեղում։ Թվային արժեքները կարելի է ճշտել ներքևում։')
        target = st.radio('Նշվող կետ',targets,horizontal=True,key='click_target')

        if calibration_mode == 'Պատրաստի ֆայլ':
            names = [str(p.relative_to(ROOT)) for p in sorted((ROOT/'configs').glob('calibration-*.json'))]
            default = PRESETS.get(demos[demo_name]) if source_kind == 'Ցուցադրական տեսանյութ' else None
            if names:
                chosen = st.selectbox('Տրամաչափման ֆայլ',names,index=names.index(default) if default in names else 0)
                calibration_data = json.loads((ROOT/chosen).read_text())
                st.caption(calibration_data.get('source',''))
            else:
                st.info('configs պանակում տրամաչափման ֆայլեր չկան։')
        elif calibration_mode == 'Ձեռքով (4 կետ)':
            c1,c2,c3 = st.columns(3)
            width_m = c1.number_input('Լայնություն, մ',0.5,100.0,7.0,0.1)
            length_m = c2.number_input('Երկարություն, մ',1.0,1000.0,50.0,1.0)
            lanes = c3.number_input('Երթևեկելի գոտիների թիվ',1,12,2)
            points = [[int(st.session_state[f'cal{i}x']),int(st.session_state[f'cal{i}y'])] for i in range(4)]
            calibration_data = dict(image_points=points,width_m=float(width_m),length_m=float(length_m),lanes=int(lanes),
                                    description='Ձեռքով մուտքագրված տրամաչափում',source='Օգտատեր')
        if calibration_data is not None:
            try:
                calibration_object = Calibration.from_dict(calibration_data)
            except (ValueError,KeyError,TypeError) as exc:
                st.error(f'Տրամաչափումը սխալ է՝ {exc}')
                calibration_data, calibration_object = None, None

        configured_line = [int(st.session_state[k]) for k in ('ax','ay','bx','by')]
        if calibration_object is not None and calibration_object.segment_share(configured_line) == 0:
            st.warning('Հիմնական գիծը չի անցնում տրամաչափված գոտով (երկնագույն)։ Հոսքի և q = k·v ստուգումը չի կատարվի. տեղափոխեք գիծը գոտու ներսում։')
        try:
            validate_line(configured_line,width,height)
        except ValueError:
            st.error('Հիմնական գծի A և B կետերը պետք է տարբեր լինեն և գտնվեն կադրի ներսում։')
            configured_line = None
        if extra_enabled:
            extra_line = [int(st.session_state[k]) for k in ('ex1','ey1','ex2','ey2')]
            try:
                validate_line(extra_line,width,height)
            except ValueError:
                st.error('Լրացուցիչ գծի կետերը պետք է տարբեր լինեն և գտնվեն կադրի ներսում։')
                extra_line = None

        overlay = source_frame.copy()
        thick = max(2,width//480)
        if calibration_object is not None:
            overlay = draw_polygon(overlay,calibration_object.image_points)
            for i,(px,py) in enumerate(calibration_object.image_points):
                if 0 <= px < width and 0 <= py < height:
                    cv2.circle(overlay,(int(px),int(py)),3*thick,(255,255,0),-1)
                    cv2.putText(overlay,str(i+1),(int(px)+4*thick,int(py)-4*thick),cv2.FONT_HERSHEY_SIMPLEX,0.5*thick,(255,255,0),thick)
        for coords,color,(la,lb) in [(configured_line,(0,255,255),('A','B')),(extra_line,(255,0,255),('A2','B2'))]:
            if coords is not None:
                a_point,b_point = tuple(map(int,coords[:2])),tuple(map(int,coords[2:]))
                cv2.line(overlay,a_point,b_point,color,thick)
                for label,point in [(la,a_point),(lb,b_point)]:
                    cv2.circle(overlay,point,3*thick,color,-1)
                    cv2.putText(overlay,label,(max(5,min(point[0]+4*thick,width-60)),max(30,point[1]-4*thick)),cv2.FONT_HERSHEY_SIMPLEX,0.6*thick,color,thick)
        display_width = min(1100,width)
        click = image_coordinates(cv2.cvtColor(overlay,cv2.COLOR_BGR2RGB),width=display_width,key=f'click-{width}x{height}')
        st.caption('Դեղին՝ հիմնական գիծ, մանուշակագույն՝ լրացուցիչ գիծ, երկնագույն՝ տրամաչափված գոտի։ Մեքենայի հենակետը շրջանակի ստորին կողմի միջնակետն է։')
        if click and click != st.session_state.get('last_click'):
            st.session_state['last_click'] = click
            scale = width/click.get('width',display_width)
            px,py = int(round(click['x']*scale)),int(round(click['y']*scale))
            keys = POINT_KEYS[target]
            st.session_state[keys[0]],st.session_state[keys[1]] = min(max(px,0),width-1),min(max(py,0),height-1)
            st.rerun()

        with st.expander('Կետերի ճշգրիտ կոորդինատներ (պիքսել)'):
            a_col,b_col = st.columns(2)
            a_col.number_input('A կետ՝ X',0,width-1,key='ax'); a_col.number_input('A կետ՝ Y',0,height-1,key='ay')
            b_col.number_input('B կետ՝ X',0,width-1,key='bx'); b_col.number_input('B կետ՝ Y',0,height-1,key='by')
            if extra_enabled:
                a_col.number_input('Լրացուցիչ A՝ X',0,width-1,key='ex1'); a_col.number_input('Լրացուցիչ A՝ Y',0,height-1,key='ey1')
                b_col.number_input('Լրացուցիչ B՝ X',0,width-1,key='ex2'); b_col.number_input('Լրացուցիչ B՝ Y',0,height-1,key='ey2')
            if calibration_mode == 'Ձեռքով (4 կետ)':
                st.caption('Տրամաչափման կետերը (հեռավոր ձախ, հեռավոր աջ, մոտ աջ, մոտ ձախ) կարող են լինել նաև կադրից դուրս։')
                for column,(i,name) in zip(st.columns(4),enumerate(CORNER_NAMES)):
                    column.number_input(f'{name}՝ X',-5*width,6*width,key=f'cal{i}x')
                    column.number_input(f'{name}՝ Y',-5*height,6*height,key=f'cal{i}y')

    st.subheader('3. Հայտնաբերում և հետագծում')
    threshold = st.slider('Վստահության շեմ',0.05,0.95,0.30,0.05,help='Նոր մեքենայի հետագծի սկզբնավորման շեմը։ Արդեն հետագծվող մեքենաները կարող են պահպանվել վստահության ժամանակավոր նվազման դեպքում։')
    devices = ['mps','cpu','cuda'] if sys.platform == 'darwin' else ['cuda','cpu','mps']
    device = st.selectbox('Սարք',devices)
    tracking_mode = st.selectbox('Հետագծում',['Ստանդարտ (ByteTrack)','Փորձարարական (շարունակականություն)'])
    mode = 'baseline' if tracking_mode.startswith('Ստանդարտ') else 'continuity'
    interval = st.selectbox('Հոսքի վերլուծության միջակայք, վայրկյան',[5,10,30,60],index=1)
    time_scale = 1.0 if live_mode else st.number_input('Ժամանակի մասշտաբ (արագացված տեսանյութ)',1.0,1000.0,1.0,0.5,
        help='Իրական վայրկյաններ տեսանյութի մեկ վայրկյանում. 4 = 4 անգամ արագացված (time-lapse) տեսանյութ։ Ժամանակը, արագությունը և ինտենսիվությունը վերահաշվարկվում են, խտությունը չի փոխվում։')
    if mode == 'continuity':
        st.caption('Կարճ ընդհատումների և դասի պատմության լրացուցիչ մշակում։ Մշակման օրինակում այն վատթարացրեց իրադարձությունների համընկնումը. օգտագործեք հետազոտության համար։')
    if uploaded is not None:
        st.caption(f'Ֆայլ՝ {uploaded.name}, չափ {uploaded.size/1024/1024:.1f} ՄԲ')
    examples = []
    if selected and not live_mode:
        for p in (ROOT/'outputs').glob('demo-*/summary.json'):
            saved = json.loads(p.read_text())
            saved_mode = saved.get('tracking',{}).get('mode','baseline')
            if saved['weights'] == str(ROOT/selected) and saved.get('source_video',str(demo)) == str(demo) and saved_mode == mode:
                examples.append(p.parent)
    example = max(examples,key=lambda p:(p/'summary.json').stat().st_mtime) if examples else None
    if source_kind == 'Ցուցադրական տեսանյութ' and example is not None:
        if st.button('Ցույց տալ պահպանված օրինակը'):
            st.session_state['result_directory'] = str(example)

    running = st.session_state.get('running_job')
    if running and Path(running['dir']).exists():
        render_running_job(running)
    elif st.button('Մշակել տեսանյութը',disabled=not available or selected is None or configured_line is None,type='primary'):
        job = ROOT/'outputs'/f'ui-{uuid.uuid4().hex[:12]}'
        job.mkdir(parents=True)
        if source_kind == 'Սեփական ֆայլ':
            source = job/('input'+Path(uploaded.name).suffix.lower())
            source.write_bytes(uploaded.getvalue())
        elif live_mode:
            source = live_url
        else:
            source = demo
        command = [sys.executable,'-m','traffic_cnn.cli','analyze','--video',str(source),
                   '--weights',str(ROOT/selected),'--output',str(job/'results'),
                   '--line',*map(str,configured_line),'--conf',str(threshold),'--device',device,
                   '--interval-seconds',str(interval),'--classes','car,van,truck,bus,motorcycle',
                   '--imgsz',str(inference_size)]
        if live_mode:
            command += ['--max-seconds',str(live_seconds)]
        if time_scale != 1:
            command += ['--time-scale',str(time_scale)]
        if tile_size:
            command += ['--tile',str(tile_size)]
        if extra_line is not None:
            command += ['--extra-line',*map(str,extra_line)]
        if calibration_data is not None:
            (job/'calibration.json').write_text(json.dumps(calibration_data,ensure_ascii=False,indent=2))
            command += ['--calibration',str(job/'calibration.json')]
        command.append('--baseline-tracking' if mode == 'baseline' else '--continuity-tracking')
        log_handle = (job/'analysis.log').open('w')
        process = subprocess.Popen(command,cwd=ROOT,stdout=log_handle,stderr=subprocess.STDOUT,text=True)
        st.session_state['running_job'] = dict(dir=str(job),pid=process.pid,live=live_mode,started=time.time())
        PROCESSES[process.pid] = process
        st.rerun()
    if st.session_state.get('job_error'):
        st.error('Մշակումն ավարտվեց սխալով։ Մանրամասները՝ մատյանում։')
        st.code(st.session_state.pop('job_error'))
    if 'result_directory' in st.session_state and (Path(st.session_state['result_directory'])/'summary.json').exists():
        result_dir = Path(st.session_state['result_directory'])
        report = json.loads((result_dir/'summary.json').read_text())
        st.divider()
        st.header('Արդյունքներ')
        st.caption(f"Տեսանյութ՝ {Path(report.get('source_video','video')).name} · մոդել՝ {Path(report['weights']).parent.parent.name} · մուտք {report.get('imgsz','—')} px · շեմ {report['confidence']:.2f} · տևողություն {report['duration_seconds']:.2f} վ")
        a,b,c = st.columns(3)
        a.metric('Հատումներ (հիմնական գիծ)',report['crossings'])
        b.metric('Հոսքի ինտենսիվություն, մեքենա/ժամ',f"{report['flow_vehicles_per_hour']:.0f}")
        c.metric('Մշակման արագություն, կադր/վ',f"{report['processing_fps']:.1f}")
        if report.get('time_scale',1) != 1:
            st.caption(f"Ժամանակի մասշտաբ՝ ×{report['time_scale']:g}. տևողությունը, արագությունը և ինտենսիվությունը ներկայացված են իրական ժամանակով։")
        move = report.get('motion') or {}
        if move.get('per_real_second') is not None:
            st.caption(f"Մեքենաների տեսանելի շարժը՝ {move['median_box_heights_per_frame']:.3f} շրջանակի բարձրություն/կադր "
                       f"({move['per_real_second']:.2f}/վ իրական ժամանակով)։ Արագացված տեսանյութում այս արժեքը սովորականից զգալիորեն մեծ է։")
        guard = report.get('duplicate_guard')
        if guard and guard['enabled'] and guard['suppressed']:
            st.caption(f"Կրկնակի հաշվարկից պաշտպանություն. {guard['suppressed']} հատում չի հաշվվել, քանի որ նույն կադրում դրա շրջանակը համընկնում է արդեն հաշվված մեքենայի շրջանակին (տես duplicate_crossings.csv)։")
        if 'speed' in report:
            spot, density = report['speed']['at_counting_line'], report['density']
            a,b,c,d = st.columns(4)
            a.metric('Միջին արագություն գծում, կմ/ժ',fmt(spot['time_mean_kmh']))
            b.metric('85-րդ տոկոսային արագություն, կմ/ժ',fmt(spot['p85_kmh']))
            c.metric('Խտություն, մեքենա/կմ/գոտի',fmt(density['mean_density_per_km_per_lane']))
            los = density['level_of_service']
            d.metric('Սպասարկման մակարդակ (LOS)',los or '—',LOS_DESCRIPTION.get(los,''),delta_color='off')
            if report.get('plausibility_warning'):
                reasons = {'median_speed_above_160':'մեդիան արագությունը > 160 կմ/ժ','speeds_above_250':'չափումների զգալի մասը > 250 կմ/ժ',
                           'flow_above_lane_capacity':'ինտենսիվությունը > 2400 մեքենա/ժամ/գոտի (գերազանցում է թողունակությունը)',
                           'flow_density_speed_mismatch':'q-ն և k·v-ն տարբերվում են ավելի քան 2 անգամ'}
                found = '; '.join(reasons.get(i,i) for i in report.get('plausibility_issues',[])) or 'մեդիանը > 160 կմ/ժ կամ չափումների զգալի մասը > 250 կմ/ժ'
                st.error(f'Չափումները ֆիզիկապես անհավանական են ({found})։ Տեսանյութը, հավանաբար, արագացված է (time-lapse), հետագծիչը կրկնակի է հաշվում մեքենաները, կամ տրամաչափումը (չափեր, գոտիների քանակ) սխալ է։ Արագությունն ու ինտենսիվությունը ֆիզիկապես վավեր չեն։')
                raw = report['speed'].get('raw_median_kmh')
                if raw:
                    st.info(f"Բոլոր չափումների մեդիանը (ներառյալ մերժվածները)՝ {raw:.0f} կմ/ժ։ Եթե իրական միջին արագությունը, օրինակ, 100 կմ/ժ է, "
                            f"տեսանյութը մոտ {raw/100:.1f} անգամ արագացված է. նշեք «Ժամանակի մասշտաբ» դաշտում և կրկնեք վերլուծությունը։")
            if report.get('line_share_in_zone') == 0:
                st.warning('Հիմնական գիծը չի անցնում տրամաչափված գոտով. գոտու հոսքը և q = k·v ստուգումը չեն հաշվարկվել։')
            fr = report.get('fundamental_relation')
            if fr and fr['density_times_speed']:
                st.caption(f"Հոսքի հիմնական հավասարում q = k·v (միայն տրամաչափված գոտում). չափված q = {fr['measured_flow_per_hour']:.0f} մեք/ժ, k·vₛ = {fr['density_times_speed']:.0f} մեք/ժ (տարբերություն {100*fr['relative_difference']:.0f}%)։ Կարճ տեսանյութում տարբերությունը պայմանավորված է փոքր նմուշով։")
            share = report['speed'].get('crossings_with_speed_share')
            if share is not None and share < 0.5:
                st.warning(f'Արագությունը չափվել է հատումների միայն {100*share:.0f}%-ի համար. հետագծերը կարճ են կամ դուրս են տրամաչափված գոտուց։')
        direction_labels = line_direction_labels(report['line'])
        left,right = st.columns(2)
        left.write('**Ուղղություններ**')
        left.dataframe(pd.DataFrame([{'Ուղղություն':direction_labels.get(k,k),'Հատումներ':v} for k,v in report['by_direction'].items()]),hide_index=True)
        right.write('**Տրանսպորտի դասեր**')
        right.dataframe(pd.DataFrame([{'Դաս':CLASS_LABELS.get(k,k),'Հատումներ':v} for k,v in report['by_class'].items()]),hide_index=True)
        groups, heavy_share = vehicle_groups(report['by_class'])
        if heavy_share is not None:
            right.caption(f"Ծանր տրանսպորտ (բեռնատար + ավտոբուս)՝ {groups['heavy']} ({100*heavy_share:.0f}%), թեթև (մարդատար + ֆուրգոն)՝ {groups['light']}, մոտոցիկլ՝ {groups['motorcycle']}։ Բեռնատարն ու ավտոբուսը երբեմն շփոթվում են, ուստի ծանր տրանսպորտի ընդհանուր թիվն ավելի հուսալի է։")
        if len(report.get('lines',[])) > 1:
            st.write('**Հաշվման գծեր**')
            st.dataframe(pd.DataFrame([{'Գիծ':l['line_id'],'Կոորդինատներ':str([round(v) for v in l['coordinates']]),'Հատումներ':l['crossings'],'Մեքենա/ժամ':round(l['flow_vehicles_per_hour'])} for l in report['lines']]),hide_index=True)
        if (result_dir/'frame_stats.csv').exists():
            statistics = pd.read_csv(result_dir/'frame_stats.csv')
            chart_columns = {'visible_tracked_vehicles':'Մեքենաներ կադրում','cumulative_crossings':'Կուտակային հատումներ'}
            if 'vehicles_in_zone' in statistics:
                chart_columns['vehicles_in_zone'] = 'Մեքենաներ գոտում'
            st.subheader('Դինամիկա ժամանակի ընթացքում')
            st.line_chart(statistics.set_index('time_seconds')[list(chart_columns)].rename(columns=chart_columns),x_label='Ժամանակ, վ',y_label='Քանակ')
            events = pd.read_csv(result_dir/'crossings.csv')
            windows = pd.DataFrame(flow_windows(events.to_dict('records'),statistics.to_dict('records'),report.get('time_fps',report['source_fps']),report.get('interval_seconds',interval)))
            st.subheader('Հոսքն ըստ ժամանակային միջակայքերի')
            st.bar_chart(windows.set_index('start_seconds')[['negative_to_positive','positive_to_negative']].rename(columns=direction_labels),x_label='Միջակայքի սկիզբ, վ',y_label='Հատումներ')
            if 'mean_speed_kmh' in windows:
                left_chart,right_chart = st.columns(2)
                left_chart.write('**Միջին արագություն, կմ/ժ**')
                left_chart.bar_chart(windows.set_index('start_seconds')[['mean_speed_kmh']].rename(columns={'mean_speed_kmh':'Միջին արագություն, կմ/ժ'}),x_label='Միջակայքի սկիզբ, վ',y_label='կմ/ժ')
                right_chart.write('**Խտություն, մեքենա/կմ**')
                right_chart.bar_chart(windows.set_index('start_seconds')[['mean_density_per_km']].rename(columns={'mean_density_per_km':'Խտություն, մեք/կմ'}),x_label='Միջակայքի սկիզբ, վ',y_label='մեք/կմ',color='#2a9d8f')
            names = {'start_seconds':'Սկիզբ, վ','end_seconds':'Վերջ, վ','duration_seconds':'Տևողություն, վ','crossings':'Հատումներ','negative_to_positive':direction_labels['negative_to_positive'],'positive_to_negative':direction_labels['positive_to_negative'],'mean_visible_tracked_vehicles':'Միջինը կադրում','peak_visible_tracked_vehicles':'Առավելագույնը կադրում','event_rate_per_hour':'Մեքենա/ժամ (վերահաշվարկ)','frame_count':'Կադրեր','mean_speed_kmh':'Միջին արագություն, կմ/ժ','space_mean_speed_kmh':'Տարածական միջին արագություն, կմ/ժ','mean_density_per_km':'Խտություն, մեք/կմ'}
            st.dataframe(windows.rename(columns=names),hide_index=True)
            st.download_button('Ներբեռնել հոսքն ըստ միջակայքերի (CSV)',windows.to_csv(index=False).encode('utf-8'),file_name='flow_windows.csv',mime='text/csv')
        if (result_dir/'tracks_summary.csv').exists():
            tracks = pd.read_csv(result_dir/'tracks_summary.csv')
            if 'median_speed_kmh' in tracks and tracks['median_speed_kmh'].notna().any():
                st.subheader('Արագությունների բաշխում')
                values = tracks['median_speed_kmh'].dropna()
                counts, edges = np.histogram(values,bins=np.arange(0,max(values.max(),20)+10,10))
                st.bar_chart(pd.DataFrame({'Մեքենաներ':counts},index=pd.Index([int(e)+5 for e in edges[:-1]],name='կմ/ժ')),x_label='Արագություն (10 կմ/ժ միջակայքի կենտրոն), կմ/ժ',y_label='Մեքենաներ')
        images = [(name,label) for name,label in [('heatmap.png','Շարժման ջերմային քարտեզ'),('trajectories.png','Հետագծեր ըստ դասերի')] if (result_dir/name).exists()]
        if images:
            for column,(name,label) in zip(st.columns(len(images)),images):
                column.image(str(result_dir/name),caption=label)
        if report.get('video_codec') == 'avc1':
            st.video(str(result_dir/'annotated.mp4'))
        else:
            cap = cv2.VideoCapture(str(result_dir/'annotated.mp4'))
            ok, preview = cap.read()
            cap.release()
            if ok:
                st.image(cv2.cvtColor(preview,cv2.COLOR_BGR2RGB),caption='Առաջին մշակված կադրը')
        downloads = [('annotated.mp4','Նշագրված տեսանյութ','video/mp4'),('crossings.csv','Հատումներ (CSV)','text/csv'),
                     ('line_crossings.csv','Հատումներ ըստ գծերի (CSV)','text/csv'),('tracks.csv','Հետագծեր (CSV)','text/csv'),
                     ('tracks_summary.csv','Շարժման բնութագրեր (CSV)','text/csv'),('frame_stats.csv','Վիճակագրություն ըստ կադրերի (CSV)','text/csv'),
                     ('summary.json','Ամփոփում (JSON)','application/json')]
        columns = st.columns(4)
        for index,(name,label,mime) in enumerate([d for d in downloads if (result_dir/d[0]).exists()]):
            columns[index % 4].download_button(label,(result_dir/name).read_bytes(),file_name=name,mime=mime)
        if result_dir.name.startswith('demo-'):
            check_file = ROOT/f"reports/counting-{result_dir.name.removeprefix('demo-')}.json"
            if check_file.exists():
                check = json.loads(check_file.read_text())['temporal_event_check']
                st.info(f"Նախնական ստուգում տեսողական միջակայքերով՝ {check['matched_events']} համընկնում, {len(check['unmatched_reference_events'])} բաց թողնված, {len(check['unmatched_predicted_events'])} ավելորդ իրադարձություն։")
        st.warning('ID-ի փոխարկումը կարող է հանգեցնել կրկնակի հաշվարկի։ Ժամային ինտենսիվությունը կարճ տեսանյութի վերահաշվարկ է։ Արագության ճշտությունը կախված է տրամաչափումից՝ չափերի սխալը համամասնորեն փոխում է արագությունը։')

with evaluation_tab:
    st.subheader('Համեմատում նշագրված իրադարձությունների հետ')
    st.write('Յուրաքանչյուր նշագրված մեքենային համապատասխանում է առավելագույնը մեկ կանխատեսում։ Բաց թողումներն ու ավելորդ իրադարձությունները հաշվվում են անկախ ընդհանուր քանակի համընկնումից։')
    result_paths = sorted((ROOT/'outputs').glob('**/summary.json'),key=lambda p:p.stat().st_mtime,reverse=True)
    if result_paths:
        chosen_result = st.selectbox('Ստուգվող արդյունք',result_paths,format_func=lambda p:str(p.parent.relative_to(ROOT)))
        checking_summary = json.loads(chosen_result.read_text())
        template = dict(source_sha256=checking_summary['source_sha256'],fps=checking_summary['source_fps'],line=checking_summary['line'],
                        annotation_status='unverified',reference_type='Describe who annotated the original video and how',
                        point_convention='Bottom-center of vehicle box; zero-based frame indices',events=[],
                        limitations='Independent annotation verification is required.')
        st.download_button('Ներբեռնել նշագրման ձևանմուշը (JSON)',json.dumps(template,ensure_ascii=False,indent=2).encode('utf-8'),file_name='reference.json',mime='application/json')
        st.caption('events ցուցակում յուրաքանչյուր մեքենայի համար ավելացրեք մեկ գրառում՝ class, direction և frame_interval [առաջին, վերջին կադր]։')
        st.code('{"vehicle":"car-1","class":"car","direction":"negative_to_positive","frame_interval":[100,104]}',language='json')
        reference_kind = st.radio('Նշագրման աղբյուր',['Նախնական օրինակ','Սեփական JSON','Նշագրում հավելվածում'],horizontal=True)
        annotation = st.file_uploader('Իրադարձությունների նշագրում (JSON)',type=['json']) if reference_kind == 'Սեփական JSON' else None
        manual_reference = annotation_tool(checking_summary,chosen_result.parent,template) if reference_kind == 'Նշագրում հավելվածում' else None
        tolerance = st.number_input('Համընկնման թույլատրելի շեղում, կադր',0,100,6)
        if reference_kind == 'Նախնական օրինակ' or annotation is not None or manual_reference is not None:
            try:
                reference = manual_reference if manual_reference is not None else json.loads(annotation.getvalue()) if annotation is not None else json.loads((ROOT/'reports/video-reference.json').read_text())
                if not isinstance(reference,dict):
                    raise ValueError('JSON նշագրումը պետք է լինի օբյեկտ։')
                if not reference.get('events'):
                    st.info('Իրադարձությունների ցուցակը դատարկ է։')
                else:
                    predicted = pd.read_csv(chosen_result.parent/'crossings.csv').to_dict('records')
                    comparison = evaluate_run(checking_summary,reference,predicted,int(tolerance))
                    a,b,c = st.columns(3)
                    a.metric('Համընկած իրադարձություններ',comparison['temporal_event_check']['matched_events'])
                    b.metric('Բաց թողնված',len(comparison['temporal_event_check']['unmatched_reference_events']))
                    c.metric('Ավելորդ',len(comparison['temporal_event_check']['unmatched_predicted_events']))
                    a,b,c = st.columns(3)
                    percent = lambda v: None if v is None else 100*v
                    a.metric('Precision',fmt(percent(comparison['event_precision']),1,'%'))
                    b.metric('Recall',fmt(percent(comparison['event_recall']),1,'%'))
                    c.metric('F1',fmt(percent(comparison['event_f1']),1,'%'))
                    st.write('Դասի սխալներ համընկածների մեջ՝',len(comparison['temporal_event_check']['matched_class_disagreements']))
                    with st.expander('Համընկնումներ և սխալներ'):
                        st.json(comparison['temporal_event_check'])
                    st.download_button('Ներբեռնել ստուգման հաշվետվությունը (JSON)',json.dumps(comparison,ensure_ascii=False,indent=2).encode('utf-8'),file_name='counting-evaluation.json',mime='application/json')
            except (ValueError,KeyError,TypeError,OSError) as exc:
                messages = {'Reference source_sha256 must match the analyzed video':'Նշագրումը վերաբերում է այլ տեսանյութի։',
                            'Reference and analysis counting lines differ':'Նշագրման գիծը տարբերվում է մշակման գծից։',
                            'Reference and analysis FPS differ':'Կադրային հաճախականությունը չի համապատասխանում։',
                            'Reference frame_interval must be within the video':'Միջակայքերը պետք է լինեն տեսանյութի ներսում։',
                            'CSV event count differs from summary':'CSV-ի իրադարձությունների քանակը չի համապատասխանում ամփոփմանը։',
                            'Reference events must be objects':'Յուրաքանչյուր իրադարձություն պետք է լինի JSON օբյեկտ։',
                            'Invalid reference direction or vehicle class':'Անհայտ դաս կամ ուղղություն։'}
                st.error(f'Գնահատումը չկատարվեց՝ {messages.get(str(exc),str(exc))}')
    else:
        st.info('Նախ մշակեք տեսանյութ։')

with experiment_tab:
    st.subheader('Ավարտված փորձեր')
    rows = [{'Փորձ':r['name'],'Սկզբնավորում':r['initialization'],'Էպոխներ':r.get('epochs_completed',r['epochs_requested']),'Մուտք, px':r['imgsz'],
             'Val mAP50–95, %':100*r['validation']['metrics/mAP50-95(B)'],'Test mAP50, %':100*r['test']['metrics/mAP50(B)'],'Test mAP50–95, %':100*r['test']['metrics/mAP50-95(B)']} for r in completed]
    if rows:
        st.dataframe(pd.DataFrame(rows),hide_index=True)
        st.caption('Լավագույն էպոխը և մոդելն ընտրվում են validation-ով. test-ը չի մասնակցում ընտրությանը։')
    resolution_file = ROOT/'reports/resolution-comparison.json'
    if resolution_file.exists():
        resolution = json.loads(resolution_file.read_text())
        st.subheader('CNN մուտքի չափի ազդեցությունը')
        st.dataframe([{'Մուտք, px':int(size),'Val mAP50-95, %':100*result['validation']['metrics']['metrics/mAP50-95(B)'],'Test mAP50, %':100*result['test']['metrics']['metrics/mAP50(B)'],'Test mAP50-95, %':100*result['test']['metrics']['metrics/mAP50-95(B)']} for size,result in resolution['sizes'].items()],hide_index=True)
    external_file = ROOT/'reports/detrac-external-comparison.json'
    if external_file.exists():
        external = json.loads(external_file.read_text())
        if 'rows' in external:
            st.subheader('Արտաքին ստուգում՝ UA-DETRAC')
            st.dataframe([{'Տեսանյութ':r['sequence'],'Մոդել':r['model'],'Մուտք, px':r['imgsz'],'Էտալոն':r['reference'],'Գտնված':r['predicted'],'Բաց թողնված':r['missed'],'Ավելորդ':r['extra'],'F1, %':None if r['event_f1'] is None else 100*r['event_f1'],'AP50, %':100*r['vehicle_AP50'],'AP50–95, %':100*r['vehicle_AP50_95']} for r in external['rows']],hide_index=True)
    for r in completed:
        directory = Path(r['training_directory'])
        if (directory/'results.png').exists():
            with st.expander(f"{r['name']} · ուսուցման կորեր"):
                st.image(str(directory/'results.png'))
                st.dataframe(pd.DataFrame(r['test_by_class']).T)
    for log in sorted((ROOT/'reports').glob('train-*.log')):
        with st.expander(log.name):
            text = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]','',log.read_text(errors='replace')).replace('\r','\n')
            st.code('\n'.join(text.splitlines()[-12:]))

with data_tab:
    dataset = ROOT/'reports/dataset.json'
    if dataset.exists():
        report = json.loads(dataset.read_text())
        st.write('VisDrone2019-DET · տրանսպորտի հինգ դաս')
        st.json(report['splits'])
        st.write('Սահմանափակումներ՝',report['limitations'])
    st.markdown('[VisDrone պաշտոնական աղբյուր](https://github.com/VisDrone/VisDrone-Dataset) · [UA-DETRAC](https://arxiv.org/abs/1511.04136)')
    if (ROOT/'reports/dataset-diagnostics.png').exists():
        st.image(str(ROOT/'reports/dataset-diagnostics.png'),caption='Շրջանակների չափերը և դասերի բաշխումը')
