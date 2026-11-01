"""Local manual event annotation on original video frames."""
import json
from pathlib import Path
import uuid
import cv2
import streamlit as st
from .geometry import direction_labels


@st.cache_data(max_entries=8,show_spinner=False)
def reference_frame(source, frame_index, line, modified):
    cap = cv2.VideoCapture(source)
    try:
        cap.set(cv2.CAP_PROP_POS_FRAMES,frame_index)
        ok,frame = cap.read()
        if not ok:
            return None
        cv2.line(frame,tuple(map(int,line[:2])),tuple(map(int,line[2:])),(0,255,255),4)
        if frame.shape[1] > 1280:
            frame = cv2.resize(frame,(1280,round(frame.shape[0]*1280/frame.shape[1])))
        return cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
    finally:
        cap.release()


def annotation_tool(summary, result_directory, template):
    source = Path(summary.get('source_video',''))
    if not source.is_file():
        st.info('Սկզբնական տեսանյութը հասանելի չէ։ Նշագրման համար վերականգնեք ֆայլը նշված ուղով։')
        return None
    annotation_path = result_directory/'manual-reference.json'
    key = f"manual-reference-{summary['source_sha256']}-{summary['line']}"
    if key not in st.session_state:
        st.session_state[key] = json.loads(annotation_path.read_text()) if annotation_path.exists() else dict(template,events=[])
    reference = st.session_state[key]
    st.caption('Դիտեք սկզբնական կադրերը և յուրաքանչյուր ֆիզիկական մեքենայի հատումը նշեք մեկ անգամ։ Մոդելի կանխատեսումներն այստեղ ցուցադրված չեն։ Պահպանումը չի հաստատում նշագրման անկախությունը կամ ճշտությունը։')
    maximum = summary['frames']-1
    index = st.slider('Սկզբնական տեսանյութի կադր',0,maximum,0,key='annotation-frame') if maximum > 0 else 0
    preview = reference_frame(str(source),index,tuple(summary['line']),source.stat().st_mtime_ns)
    if preview is not None:
        st.image(preview,caption=f'Կադր {index}, ժամանակ {index/summary["source_fps"]:.3f} վ։ Ինդեքսները սկսվում են զրոյից։')
    labels = direction_labels(summary['line'])
    with st.form('add-reference-event',clear_on_submit=False):
        vehicle = st.text_input('Մեքենայի անվանումը նշագրման մեջ',value=f'vehicle-{len(reference["events"])+1}')
        category = st.selectbox('Նշագրված մեքենայի դաս',['car','van','truck','bus','motorcycle'])
        direction = st.selectbox('Նշագրված մեքենայի ուղղություն',list(labels),format_func=lambda d:labels[d])
        left,right = st.columns(2)
        first = left.number_input('Միջակայքի առաջին կադր',0,maximum,index)
        last = right.number_input('Միջակայքի վերջին կադր',0,maximum,index)
        added = st.form_submit_button('Ավելացնել նշագրման իրադարձություն')
    if added:
        if first > last:
            st.error('Առաջին կադրը չի կարող լինել վերջինից հետո։')
        else:
            reference['events'].append({'id':uuid.uuid4().hex,'vehicle':vehicle,'class':category,'direction':direction,'frame_interval':[int(first),int(last)]})
            reference.update(reference_type='Manually entered by the user using original frames in the local application',annotation_status='user_entered_unverified')
            temporary = annotation_path.with_suffix('.tmp')
            temporary.write_text(json.dumps(reference,ensure_ascii=False,indent=2))
            temporary.replace(annotation_path)
            st.success('Իրադարձությունը պահպանված է տեղում։')
    if reference['events']:
        st.dataframe(reference['events'],hide_index=True)
        selected_id = st.selectbox('Ջնջվող իրադարձություն',[e['id'] for e in reference['events']],format_func=lambda identity:next(e['vehicle']+': '+str(e['frame_interval']) for e in reference['events'] if e['id']==identity))
        if st.button('Ջնջել ընտրված իրադարձությունը'):
            reference['events'] = [e for e in reference['events'] if e['id'] != selected_id]
            annotation_path.write_text(json.dumps(reference,ensure_ascii=False,indent=2))
            st.rerun()
    st.download_button('Ներբեռնել մուտքագրված նշագրումը',json.dumps(reference,ensure_ascii=False,indent=2).encode('utf-8'),file_name='manual-reference.json',mime='application/json')
    return reference
