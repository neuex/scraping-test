import urllib.request, urllib.error
import csv
import random
import logging
import sys
from time import sleep, time
from bs4 import BeautifulSoup
from enum import Enum
from retry import retry

BASE_URL = "https://www.cosmetic-info.jp"
LIST_PAGE_URL = BASE_URL + "/prod/result.php?cq%5B0%5D=0&jcln%5B0%5D=&jcln%5B1%5D=&jcln%5B2%5D=&-f=saler&-d=a&-p=all"
CSV_FILE_NAME = "scraping.csv"

### Loggerの設定
logger = logging.getLogger('Logger')
logger.setLevel(10)
fh = logging.FileHandler('scraping.log', encoding='utf-8')
logger.addHandler(fh)
sh = logging.StreamHandler()
logger.addHandler(sh)
formatter = logging.Formatter('%(asctime)s:%(lineno)d:%(levelname)s:%(message)s')
fh.setFormatter(formatter)
sh.setFormatter(formatter)

def global_except_hook(exctype, value, traceback):
    if exctype == KeyboardInterrupt:
        logger.warn('強制終了しました')
    else:
        logger.error(value)
        logger.error(traceback)
        sys.__excepthook__(exctype, value, traceback)
sys.excepthook = global_except_hook
###############

class Mode(Enum):
        ADD = 1
        WRITE = 2

# 一覧ページから各商品ページへのリンク取得
def fetch_page_links():
    root_html = urllib.request.urlopen(LIST_PAGE_URL)
    root = BeautifulSoup(root_html, 'lxml')
    return [link_elm.get('href') for link_elm in root.find(class_="listview").find('tbody').find_all('a')]

# 商品ページから商品情報を取得
@retry(urllib.error.HTTPError, tries=3, delay=1, logger=logger)
def fetch_item_data(url):
    detail_html = urllib.request.urlopen(BASE_URL + "/prod/" + url)
    detail_root = BeautifulSoup(detail_html, 'lxml')

    item_rows = detail_root.find(class_='formview').find_all('tr', recursive = False)

    # 商品情報取得
    id = url.split('=')[1]                                              # 0: id
    item_name = item_rows[0].find('td').text                            # 1: 商品名
    distributor = item_rows[1].find('td').find('a').text                # 2: 販売元
    release_date = item_rows[2].find('td').find('a').text               # 3: 発売日
    dosage_form_class_spans = item_rows[3].find('td').find_all('a')
    dosage_form_class_texts = [a.text for a in dosage_form_class_spans]
    dosage_form_classes = " ".join(dosage_form_class_texts)             # 4: 剤型分類
    type_ = item_rows[4].find('td').text                                # 5: 種別
    ingredient_list = [a.text for a in item_rows[5].find('td').find('ol').find_all('a')] # 6-: 成分リスト

    return [id,item_name,distributor,release_date,dosage_form_classes, type_] + ingredient_list

# CSV書き込み
def write_csv(data, mode=Mode.WRITE):
    with open(CSV_FILE_NAME, 'a' if mode == Mode.ADD else 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, lineterminator='\n')
        writer.writerow(data)


max_ingredient_list_size = 0 # ヘッダー生成用
i = 0 #進捗用

logger.info("件数取得開始")

links = fetch_page_links()
item_count = len(links)

logger.info("対象商品数：{}件".format(item_count))

for link_url in links:
    id = link_url.split('=')[1]
    
    # 進捗出力
    print(str(i+1) + '/' + str(item_count))

    try:
        item_data = fetch_item_data(link_url)
    
        # 成分リストのサイズ取得（ヘッダー用）
        ingredient_list_size = len(item_data) - 6
        max_ingredient_list_size = ingredient_list_size if max_ingredient_list_size < ingredient_list_size else max_ingredient_list_size

        write_csv(item_data, Mode.WRITE if i == 0 else Mode.ADD)
    except urllib.error.HTTPError as e:
        logger.error('ItemId: %(id)s, %(error)s', {'id': id, 'error': e })
    except Exception as e:
        logger.error('ItemId: %(id)s, %(error)s', {'id': id, 'error': e })
    finally:
        # DoS攻撃防止のため1秒スリープ
        sleep(random.uniform(0.8, 1.2))
        i+=1

        # TODO: 削除する
        # if i == 10:
        #     break

# CSVヘッダー生成
ingredient_list_headers = list(map(lambda i:'全成分'+str(i+1), range(max_ingredient_list_size)))
header_row = ['ID', '商品名', '発売元', '発売日', '剤型分類', '種類'] + ingredient_list_headers

logger.info("csvヘッダー出力開始")
# ヘッダー出力
with open(CSV_FILE_NAME, newline='') as f:
    r = csv.reader(f)
    data = [line for line in r]
with open(CSV_FILE_NAME,'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f, lineterminator='\n')
    w.writerow(header_row)
    w.writerows(data)

logger.info("csv出力完了")
input('キーを押して終了')