import urllib.request, urllib.error
from time import sleep
import csv
from bs4 import BeautifulSoup

BASE_URL = "https://www.cosmetic-info.jp"
list_page_url = BASE_URL + "/prod/result.php?cq%5B0%5D=0&jcln%5B0%5D=&jcln%5B1%5D=&jcln%5B2%5D=&-f=saler&-d=a&-p=all"

def scrape():
    # 一覧ページから各商品ページへのリンク
    root_html = urllib.request.urlopen(list_page_url + 'all')
    print('load complete')
    root = BeautifulSoup(root_html, 'lxml')
    print('parse complete')
    links = [link_elm.get('href') for link_elm in root.find(class_="listview").find('tbody').find_all('a')]

    item_count = len(links)
    item_info_list = []
    max_ingredient_list_size = 0 #ヘッダー用
    i = 1 #進捗用

    ## 各商品ページから商品情報を取得
    for link_url in links:
        detail_html = urllib.request.urlopen(BASE_URL + "/prod/" + link_url)
        detail_root = BeautifulSoup(detail_html, 'lxml')

        item_rows = detail_root.find(class_='formview').find_all('tr', recursive = False)

        # 商品情報取得
        id = link_url.split('=')[1]
        item_name = item_rows[0].find('td').text
        distributor = item_rows[1].find('td').find('a').text
        release_date = item_rows[2].find('td').find('a').text
        dosage_form_class_spans = item_rows[3].find('td').find_all('a')
        dosage_form_class_texts = [a.text for a in dosage_form_class_spans]
        dosage_form_classes = " ".join(dosage_form_class_texts)
        type_ = item_rows[4].find('td').text
        ingredient_list = [a.text for a in item_rows[5].find('td').find('ol').find_all('a')]

        item_info = [id,item_name,distributor,release_date,dosage_form_classes, type_] + ingredient_list

        # 成分リストのサイズ取得（ヘッダー用）
        ingredient_list_size = len(ingredient_list)
        max_ingredient_list_size = ingredient_list_size if max_ingredient_list_size < ingredient_list_size else max_ingredient_list_size

        # 商品情報リストに追加
        item_info_list.append(item_info)

        # 進捗出力
        print(str(i) + '/' + str(item_count))

        # DoS攻撃防止のため1秒スリープ
        sleep(1)
        i+=1

        if i == 3:
            break

    # CSVヘッダー生成
    ingredient_list_headers = list(map(lambda i:'全成分'+str(i+1), range(max_ingredient_list_size)))
    header_row = ['ID', '商品名', '発売元', '発売日', '剤型分類', '種類'] + ingredient_list_headers
    item_info_list.insert(0,header_row)

    return item_info_list

csv_data = scrape()
with open('scraping.csv', 'w') as f:
    writer = csv.writer(f, lineterminator='\n')
    writer.writerows(csv_data)