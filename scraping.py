import time
from playwright.sync_api import sync_playwright, Playwright
import re
import pandas as pd
import json
from tqdm import tqdm

# 게시판에서 게시물 링크를 추출하는 함수
def run1(playwright: Playwright, check_point1, batch1=100):
    # 체크포인트가 없는 경우
    if check_point1 == 4000:
        # 게시물 링크 저장을 위한 리스트
        links = {}
    # 체크포인트가 있는 경우 기존의 json 파일을 읽어오기
    else:
        with open('links.json', 'r') as f:
            links = json.load(f)

    # 구인구직 게시판에서 게시물 링크를 가져오기
    # 구인구직 게시판의 몇번째 페이지까지 가져올지 정하기 (중복을 없애기 위해 역순으로 for문 진행)
    for i in tqdm(range(check_point1, check_point1 - batch1, -1)):
        chromium = playwright.chromium
        browser = chromium.launch(headless=False)
        page = browser.new_page()
        p = f'https://www.mule.co.kr/bbs/info/recruit?page={i}&userid=&isAdmin=false&isPartner=false&of=wdate&od=desc&'
        page.goto(p)    
        
        # 프리미엄을 제외한 게시물 가져오기
        for j in range(148, 179, 1):
            try:
                link = page.locator(f'#board > div.board-list-wrapper.cf > table > tbody > tr:nth-child({j}) > td.title > a').get_attribute('href')
            except:
                continue
            link = 'https://www.mule.co.kr' + link
            # 링크의 idx부분을 따로 저장 (중복을 제거하기 위해)
            start = link.find('idx=')
            end = link.find('&')
            link_idx = link[start + 4:end]
            links[link_idx] = link
            # time.sleep(0.5)
        browser.close()

    with open('links.json', 'w') as f:
        json.dump(links, f, indent=4)
    return
    
# 저장된 각 링크에서 데이터를 추출하는 함수
def run2(playwright: Playwright, check_point2, batch2=1000):
    # 추출할 데이터 목록
    global user
    user = {'user_id':[],
            'user_name':[],
            'comm_level':[], # -1
            'score':[], # -1
            'point':[], # -1
            'profile_pic':[],
            'medal':[],
            'certification':[],
            'intro':[],
            'interest':[]}
    global post
    post = {'post_id':[],
            'title':[],
            'author_id':[],
            'date':[],
            'view_cnt':[], # -1
            'comment_cnt':[], # -1
            'rec_cnt':[], # -1
            'category':[],
            'option':[],
            'location':[], # : 활동 지역
            'addr':[], # : 모집 장소
            'phone':[],
            'page':[],
            'main':[],
            'img':[],
            'video':[]
            }
    global comment
    comment = {'comment_id':[],
               'post_id':[],
               'author_id':[],
               'upper_cmt':[], # -1
               'date':[],
               'rec_cnt':[], # 0
               'main':[]
               }
    
    # 링크가 저장된 json 파일을 읽어오기
    with open('links.json', 'r') as f:
        links = json.load(f)
    links = list(links.values())[check_point2:check_point2 + batch2]

    # 이어서 하는 경우 게시물 아이디와 댓글 아이디가 이어지도록 post_id와 comment_id를 받아와서 사용
    if check_point2 == 0:
        post_idx = 0
        cmt_idx = 0
    else:
        # 이어붙일 이전의 데이터프레임 읽어오기
        user_df = pd.read_csv('user_sample.csv', index_col=0, encoding='utf-8-sig').reset_index(drop=True)
        post_df = pd.read_csv('post_sample.csv', index_col=0, encoding='utf-8-sig').reset_index(drop=True)
        comment_df = pd.read_csv('comment_sample.csv', index_col=0, encoding='utf-8-sig').reset_index(drop=True)
        # 가장 마지막 post_id와 comment_id를 읽어와서 이어서 사용
        post_idx = int(post_df['post_id'][len(post_df) - 1])
        cmt_idx = int(comment_df['comment_id'][len(comment_df) - 1])

    # 가져온 게시물 링크에서 정보 추출
    for link in tqdm(links):
        chromium = playwright.chromium
        browser = chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(link, wait_until='load', timeout=100000)
        # time.sleep(10)
        
        # 존재하지 않는 글인지 판단
        try:
            txt = page.locator('#bbsContent_textarea').inner_text()
        # 존재하지 않는 글인 경우
        except:
            browser.close()
            continue

        # 유효한 회원이 등록한 글인지 판단
        if txt == '유효하지 않은 회원이 등록한 글입니다.':
            browser.close()
            continue

        # ----유저 테이블 데이터 추출----
        # 유저 테이블의 기본값 할당
        u_user_id = ''
        u_user_name = ''
        u_comm_level = -1
        u_score = -1
        u_point = -1
        u_profile_pic = ''
        u_medal = ''
        u_certification = ''
        u_intro = ''
        u_interest = ''

        # 사운드클라우드 api 사용 시 구조가 달라지므로 예외처리 (div:nth-child(9)로 바뀜)
        try:
            sc_check = 0
            # 유저 아이디, 닉네임, 커뮤니티 레벨 추출
            t = page.locator('#board > div.body-wrapper-board.cf > div:nth-child(8) > div > div > div.namebox > div').text_content()
            # 활동점수 추출
            score = page.locator('#board > div.body-wrapper-board.cf > div:nth-child(8) > div.profile-box > div > div.namebox > ul > li:nth-child(1) > span.mobile-br-data').text_content()
            # 누적포인트 추출
            point = page.locator('#board > div.body-wrapper-board.cf > div:nth-child(8) > div.profile-box > div > div.namebox > ul > li:nth-child(2) > b').text_content()
            # 프로필사진 추출
            user_img = page.locator('#board > div.body-wrapper-board.cf > div:nth-child(8) > div.profile-box > div').get_by_role('img').get_attribute('src')
            # 메달 수상, 인증 내역, 소개글, 관심분야 추출
            medal_lst = page.locator('#board > div.body-wrapper-board.cf > div:nth-child(8) > div.profile-box > div > ul').inner_text()
        except:
            sc_check = 1
            # 유저 아이디, 닉네임, 커뮤니티 레벨 추출
            t = page.locator('#board > div.body-wrapper-board.cf > div:nth-child(9) > div > div > div.namebox > div').text_content()
            # 활동점수 추출
            score = page.locator('#board > div.body-wrapper-board.cf > div:nth-child(9) > div.profile-box > div > div.namebox > ul > li:nth-child(1) > span.mobile-br-data').text_content()
            # 누적포인트 추출
            point = page.locator('#board > div.body-wrapper-board.cf > div:nth-child(9) > div.profile-box > div > div.namebox > ul > li:nth-child(2) > b').text_content()
            # 프로필사진 추출
            user_img = page.locator('#board > div.body-wrapper-board.cf > div:nth-child(9) > div.profile-box > div').get_by_role('img').get_attribute('src')
            # 메달 수상, 인증 내역, 소개글, 관심분야 추출
            medal_lst = page.locator('#board > div.body-wrapper-board.cf > div:nth-child(9) > div.profile-box > div > ul').inner_text()

        # 유저 아이디, 닉네임, 커뮤니티 레벨 할당
        # 일반적인 경우
        try:
            t_split = t.split(' ')
            u_user_id = t_split[1][1:-1]
            u_user_name = t_split[0]
            u_comm_level = int(t_split[2].split('.')[1])
        # 이름에 띄어쓰기가 포함되어 오류가 나는 경우
        except:
            t_split = t.split('(')
            u_user_name = t_split[0][0:-1]
            t_split2 = t_split[1].split(')')
            u_user_id = t_split2[0]
            t_split3 = t_split2[1].split('.')
            u_comm_level = int(t_split3[1])


        # 활동점수 할당
        u_score = int(score[0:-1])

        # 누적포인트 할당. 추출한 포인트 문자열에서 숫자만 선택 후 정수형으로 변환 (숫자가 아닌 문자를 ''으로 바꿔서)
        u_point = int(re.sub(r'[^0-9]', '', point))
        
        # 프로필사진 할당
        u_profile_pic = user_img

        # 메달 수상, 인증 내역, 소개글, 관심분야 할당
        # 첫 번째 값에는 '메달 수상 및 인증 내역' 고정
        # 두 번째 값에는 가입 연차와 인증 내역(인증 했을 시)을 띄어쓰기로 구분해야 함
        # -----------------두 번째 값까지는 필수로 있음----------------------
        # 세 번째 값에는 소개글을 적었다면 '소개글' 고정
        # 네 번째 값에는 소개글 내용
        # 다섯 번째 값에는 관심분야를 적었다면 '관심분야' 고정
        # 여섯 번째 값에는 관심분야 내용
        medal_split = medal_lst.split('\n')

        # 메달 추출
        medal = medal_split[1].split('차')[0] + '차'
        u_medal = medal

        # 인증 내역 추출
        crtf = medal_split[1].split('차')[1]
        # 인증 내역이 없는 경우
        if crtf == '':
            u_certification = ''
        # 인증 내역이 있는 경우
        else:
            # 앞에 있는 공백 제거
            crtf = crtf[1:]
            crtf = crtf.split('증')[0:-1]
            crtf_str = ''
            for c in crtf:
                # 증으로 split 해서 사라진 증을 다시 붙여줌
                c = c + '증'
                # 공백 제거 (본인 인증 -> 본인인증)
                c = re.sub(r'\s+', '', c)
                crtf_str = crtf_str + c + ', '
            crtf_str = crtf_str[:-2]
            u_certification = crtf_str

        # 소개글 또는 관심분야 추출
        # 소개글, 관심분야 둘 중 하나만 있는 경우
        if len(medal_split) == 4:
            if medal_split[2] == '소개글':
                u_intro = medal_split[3]
            elif medal_split[2] == '관심분야':
                u_interest = medal_split[3]
        # 소개글, 관심분야 둘 다 있는 경우
        elif len(medal_split) == 6:
            u_intro = medal_split[3]
            u_interest = medal_split[5]

        # 딕셔너리에 값 넣기
        user['user_id'].append(u_user_id)
        user['user_name'].append(u_user_name)
        user['comm_level'].append(u_comm_level)
        user['score'].append(u_score)
        user['point'].append(u_point)
        user['profile_pic'].append(u_profile_pic)
        user['medal'].append(u_medal)
        user['certification'].append(u_certification)
        user['intro'].append(u_intro)
        user['interest'].append(u_interest)

        # print(user)
        # print('---------------------------------------------------')
        
        # ----게시물 데이터 추출----
        # 게시물 테이블의 기본값 할당
        p_post_id = ''
        p_title = ''
        p_author_id = ''
        p_date = ''
        p_view_cnt = -1
        p_comment_cnt = -1
        p_rec_cnt = -1
        p_category = ''
        p_option = ''
        p_location = ''
        p_addr = ''
        p_phone = ''
        p_page = ''
        p_main = ''
        p_img = []
        p_video = []

        # 게시물 아이디 할당
        post_idx += 1
        p_post_id = str(post_idx)

        # 게시물 제목 추출
        post_title = page.locator('#board > div.body-wrapper-board.cf > h2').text_content().strip()
        p_title = post_title

        # 게시물 작성자 아이디는 이전에 추출한 유저 아이디 사용
        p_author_id = u_user_id

        # 게시물 작성일 추출
        d = page.locator('#board > div.body-wrapper-board.cf > ul.info-box.cf > li:nth-child(4) > small').text_content()
        p_date = d

        # 조회수 추출
        view = page.locator('#board > div.body-wrapper-board.cf > ul.info-box.cf > li:nth-child(1) > small').text_content()
        p_view_cnt = int(re.sub(r'[^0-9]', '', view))

        # 댓글수 추출
        cmt = page.locator('#board > div.body-wrapper-board.cf > ul.info-box.cf > li.pointer > small').text_content()
        p_comment_cnt = int(re.sub(r'[^0-9]', '', cmt))
        
        # 추천수 추출
        rec = page.locator('#board > div.body-wrapper-board.cf > ul.info-box.cf > li:nth-child(3) > small').text_content()
        p_rec_cnt = int(re.sub(r'[^0-9]', '', rec))

        # 구분, 옵션, 지역, 장소, 전화번호, 홈페이지 추출
        box = page.locator('#board > div.body-wrapper-board.cf > div.category-box.cf').inner_text()
        box_split = box.split('\n')
        for i in range(0, len(box_split), 2):
            if box_split[i] == '구분':
                p_category = box_split[i + 1]
            elif box_split[i] == '옵션':
                p_option = box_split[i + 1]
            elif box_split[i] == '지역':
                p_location = box_split[i + 1]
            elif box_split[i] == '장소':
                p_addr = box_split[i + 1]
            elif box_split[i] == '전화번호':
                page.locator('#tel-number > div.value.pointer.phoneEncode').click()
                phone = page.locator('#tel-number > div.value.phoneDecode').text_content()
                num = phone.split('\xa0')[0]
                p_phone = num
            elif box_split[i] == '홈페이지':
                p_page = box_split[i + 1]
            else:
                continue

        # 본문 내용 추출
        main_cont = page.locator('#bbsContent').all_inner_texts()
        main_txt = ''
        for cont in main_cont:
            main_txt += re.sub(r'[\n\t\xa0\ufeff\u200b\u2022\u2013\u25fc]', '', cont)
        p_main = main_txt

        # 이미지, 유튜브 링크 추출
        # 이미지 링크를 찾을 때 활용할 문자열
        img = '<img src="'
        # img 변수의 인덱스
        img_idx = 0
        # 이미지 링크를 찾았는지 확인하는 변수
        img_find = 0
        # 이미지 링크를 저장할 변수
        img_src = ''
        img_lst = []
        # 비디오 링크를 찾을 때 활용할 문자열
        video = 'src="//www.youtube.com/embed/'
        # video 변수의 인덱스
        video_idx = 0
        # 비디오 링크를 찾았는지 확인하는 변수
        video_find = 0
        # 비디오 링크를 저장할 변수
        video_src = ''
        video_lst = []

        # 유효하지 않은 회원이 등록한 글을 파악하기 위하여 본문 부분을 미리 가져오는 것으로 변경함
        # txt = page.locator('#bbsContent_textarea').inner_text()

        # inner_text()로 가져온 문자열을 처음부터 확인하며 이미지 링크 또는 비디오 링크가 있는지 확인
        for i in range(0, len(txt), 1):
            # 이미지 또는 비디오 링크를 찾은 경우 "가 나오기 전까지 추출하여 각각 리스트에 저장
            if img_find == 1:
                if txt[i] != '"':
                    img_src += txt[i]
                else:
                    img_lst.append(img_src)
                    img_src = ''
                    img_find = 0
                    img_idx = 0
            elif video_find == 1:
                if txt[i] != '"':
                    video_src += txt[i]
                else:
                    video_src = 'https://youtu.be/' + video_src
                    video_lst.append(video_src)
                    video_src = ''
                    video_find = 0
                    video_idx = 0

            # 문자열에서 링크 부분이 있는지 한 글자씩 확인
            if (img_find + video_find) == 0:
                if txt[i] == img[img_idx]:
                    img_idx += 1
                else:
                    img_idx = 0
                if txt[i] == video[video_idx]:
                    video_idx += 1
                else:
                    video_idx = 0

            # 링크 부분을 찾았는지 확인
            if img_idx == len(img):
                img_find = 1
            elif video_idx == len(video):
                video_find = 1

        # 사운드클라우드 링크가 있다면 비디오 링크 리스트에 추가
        if sc_check == 1:
            sc = page.locator('#board > div.body-wrapper-board.cf > div:nth-child(7) > div > iframe').get_attribute('src')
            video_lst.append(sc)

        p_img = img_lst
        p_video = video_lst
        
        # 딕셔너리에 값 넣기
        post['post_id'].append(p_post_id)
        post['title'].append(p_title)
        post['author_id'].append(p_author_id)
        post['date'].append(p_date)
        post['view_cnt'].append(p_view_cnt)
        post['comment_cnt'].append(p_comment_cnt)
        post['rec_cnt'].append(p_rec_cnt)
        post['category'].append(p_category)
        post['option'].append(p_option)
        post['location'].append(p_location)
        post['addr'].append(p_addr)
        post['phone'].append(p_phone)
        post['page'].append(p_page)
        post['main'].append(p_main)
        post['img'].append(p_img)
        post['video'].append(p_video)

        # print(post)
        # print('---------------------------------------------------')

        # ----댓글 데이터 추출----
        # 해당 게시물에 달린 모든 댓글 추출
        cmts = page.locator('.comment-item')
        upper_idx = 0
        for i in range(cmts.count()):
            # 댓글 테이블의 기본값 할당
            c_comment_id = ''
            c_post_id = ''
            c_author_id = ''
            c_upper_cmt = -1
            c_date = ''
            c_rec_cnt = 0
            c_main = ''
                   
            # 댓글 아이디 할당
            cmt_idx += 1
            c_comment_id = str(cmt_idx)

            # 게시물 아이디 게시물 테이블에서 가져오기
            c_post_id = p_post_id

            # 일반 댓글, 대댓글마다 구조가 다르기 때문에 구분이 필요
            # 일반 댓글의 경우
            try:
                # 작성자 추출
                cmt_author = cmts.nth(i).locator('div > div.comment-content-box > div:nth-child(1) > div.left-box.namecard').text_content().strip().split(' ')[0]
                
                # 작성 일시 추출
                cmt_date = cmts.nth(i).locator('div > div.comment-content-box > div:nth-child(1) > div.right-box.regdt').text_content()

                # 추천수 추출
                cmt_rec = cmts.nth(i).locator('div > div.comment-content-box > div:nth-child(3) > div.right-box.choice > span').text_content().strip()

                # 내용 추출
                cmt_main = cmts.nth(i).locator('div > div.comment-content-box > div.message > div').text_content()

                # 대댓글이 존재한다면 상위 댓글의 아이디를 전달하기 위해 저장
                upper_idx = cmt_idx
            except:
                # 대댓글의 경우
                try:
                    # 작성자 추출
                    cmt_author = cmts.nth(i).locator('div > div.comment-content-box > div:nth-child(2) > div.left-box.namecard').text_content().strip().split(' ')[0]
                
                    # 작성 일시 추출
                    cmt_date = cmts.nth(i).locator('div > div.comment-content-box > div:nth-child(2) > div.right-box.regdt').text_content()

                    # 추천수 추출
                    cmt_rec = cmts.nth(i).locator('div > div.comment-content-box > div:nth-child(4) > div.right-box.choice > span').text_content().strip()

                    # 내용 추출
                    cmt_main = cmts.nth(i).locator('div > div.comment-content-box > div.message.owner > div.comment-message').text_content()

                    # 대댓글의 경우 상위 댓글의 아이디를 저장
                    c_upper_cmt = str(upper_idx)
                except:
                    # 고정 댓글의 경우 건너뜀
                    cmt_idx -= 1
                    continue

            c_author_id = cmt_author
            c_date = cmt_date
            # 추천수가 없다면 0을 할당
            if cmt_rec == '':
                c_rec_cnt = 0
            else:
                c_rec_cnt = int(cmt_rec)
            c_main = re.sub(r'[\n\t\xa0\ufeff\u200b\u2022\u2013\u25fc]', '', cmt_main)

            # 딕셔너리에 값 넣기
            comment['comment_id'].append(c_comment_id)
            comment['post_id'].append(c_post_id)
            comment['author_id'].append(c_author_id)
            comment['upper_cmt'].append(c_upper_cmt)
            comment['date'].append(c_date)
            comment['rec_cnt'].append(c_rec_cnt)
            comment['main'].append(c_main)
            
        # print(comment)
        # print('------------------------')

        # time.sleep(5)
        browser.close()

        # 처음 run2 함수를 돌리는 경우
    if check_point2 == 0:
        # 추출한 데이터를 데이터프레임으로 저장
        user_df = pd.DataFrame(user)
        post_df = pd.DataFrame(post)
        comment_df = pd.DataFrame(comment)
        # csv 파일로 저장
        user_df.to_csv('user_sample.csv', encoding='utf-8-sig')
        post_df.to_csv('post_sample.csv', encoding='utf-8-sig')
        comment_df.to_csv('comment_sample.csv', encoding='utf-8-sig')
    # 이어서 run2 함수를 돌리는 경우
    else:
        # 추출한 데이터를 데이터프레임으로 저장
        user_df_tmp = pd.DataFrame(user)
        post_df_tmp = pd.DataFrame(post)
        comment_df_tmp = pd.DataFrame(comment)
        # 읽어온 데이터프레임에 추출한 데이터를 추가
        user_df = pd.concat([user_df, user_df_tmp], axis=0).reset_index(drop=True)
        post_df = pd.concat([post_df, post_df_tmp], axis=0).reset_index(drop=True)
        comment_df = pd.concat([comment_df, comment_df_tmp], axis=0).reset_index(drop=True)
        # csv 파일로 저장
        user_df.to_csv('user_sample.csv', encoding='utf-8-sig')
        post_df.to_csv('post_sample.csv', encoding='utf-8-sig')
        comment_df.to_csv('comment_sample.csv', encoding='utf-8-sig')
    return

# run1 함수 이어서 할 경우 사용 (게시판 인덱스, 역순으로 진행함) 
check_point1 = 3000
# 한 번에 몇 개의 게시판에서 게시물 링크를 추출할지
batch1 = 100

# run2 함수 이어서 할 경우 사용 (links.json 인덱스)
check_point2 = 19000
# 한 번에 몇 개의 게시글에서 데이터를 추출할지
batch2 = 1000

run_opt = 2

start_t = time.time()
with sync_playwright() as playwright:
    if run_opt == 1:
        # 게시물 링크를 가져오기
        run1(playwright, check_point1, batch1) # 3000부터 하면 됨
    elif run_opt == 2:
        run2(playwright, check_point2, batch2) # 19000부터 하면 됨
end_t = time.time()
print(f'{end_t - start_t:.1f} sec')