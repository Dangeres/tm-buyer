from bs4 import BeautifulSoup
import requests
import threading
import urllib
import random
import time
import json

# цена, ниже которой тебе необходимо вносить предмет в список частообновляемых
price_for_update = 100
# каждые сколько минут обновлять итемы которые имеют цену ниже цены указанной выше
minutes_for_update = 10
# процент для покупки расчитывается : steam/tm без учета процентов!
needpercent = 2
# минимальная цена для покупки предметов указывается в рублях
minprice = 0

# юзаем прокси для того что бы нам не давали маслину и прога не вставала по обновлению цен в стиме
proxylist = {}

# appid игры
appid = "578080"
# какой сайт нужно использовать
mainlink = 'https://market.pubg.com'
#получается на сайте https://market.pubg.com/docs/ в разделе "API ключ"
secretKey = 'secret-key'

#dont need for basic user
take_count = 100
all_items = {}
update_list = []
update = False

def get(url):
    return json.loads(requests.get(url).text)

def parse_all_names(now):
    myreq = requests.get(
        'http://steamcommunity.com/market/search/render/?query=&start=%s&count=%i&search_descriptions=0&sort_column=name&sort_dir=asc&appid=578080'%(str(now),take_count)).text
    jsonmyreq = json.loads(myreq)

    total = int(jsonmyreq['total_count'])

    tempitems = []

    soup = BeautifulSoup(jsonmyreq['results_html'], 'html.parser')
    tempnames = soup.find_all('span', class_='market_listing_item_name')

    del soup, jsonmyreq, myreq

    for element in tempnames:
        tempitems.append(element.get_text())

    return tempitems, total

def get_clear_price(price):
    return float(price[0:price.find(' ')].replace(',', '.'))

def get_proxy():
    global proxylist

    page = requests.get('https://free-proxy-list.net/anonymous-proxy.html').text
    soup = BeautifulSoup(page, 'html.parser')
    tempnames = soup.find_all('table', id='proxylisttable')[0].find_all('tbody')[0]

    for element in tempnames:
        all = element.find_all('td')
        ip = all[0].get_text()
        port = all[1].get_text()
        https = all[6].get_text()

        if https == 'yes':
            proxylist.update({'http://%s:%s' % (ip, port):True})


def get_steam_price(name):
    name = name.strip()
    nameq = urllib.parse.quote(name)

    url = 'http://steamcommunity.com/market/priceoverview/?country=US&currency=5&appid=578080&market_hash_name=%s'%nameq

    myreq = json.loads( requests.get(url).text )

    proxy = list(proxylist.keys())

    id = 0
    while myreq == None and id < len(proxy):
        myreq = json.loads(requests.get(url, proxies={'https':proxy[id]}).text)
        id += 1

    print(myreq)

    low = myreq.get('lowest_price')
    median = myreq.get('median_price')

    if low == None:
        low = median

    if median == None:
        median = low

    if median == None and low == None:
        median = 0
        low = 0
    else:
        low = get_clear_price(low)
        median = get_clear_price(median)

    price = (low+median)/2

    del nameq, low, median, url, myreq

    answer = {name:price}

    print(answer)

    # if update_list.count(name)>0:
    #     update_list.remove(update_list.index(name))

    if price <= price_for_update and price > minprice:
        print('has been added to the update list! up ^')
        update_list.append(name)

    time.sleep(random.uniform(3,4.5))

    return answer

def get_update():
    #print(" <----")
    global update_list
    count = len(update_list)

    proxy = list(proxylist.values())

    for a in range(count):
        name = update_list.pop(0)

        name = name.strip()
        nameq = urllib.parse.quote(name)

        url = 'http://steamcommunity.com/market/priceoverview/?country=US&currency=5&appid=578080&market_hash_name=%s' % nameq

        myreq = json.loads(requests.get(url).text)

        id = 0
        while myreq == None and id < len(proxy):
            myreq = json.loads(requests.get(url, proxies={'https':proxy[id]}).text)
            id += 1

        low = myreq.get('lowest_price')
        median = myreq.get('median_price')

        if low == None:
            low = median

        if median == None:
            median = low

        if low != None and median != None:

            low = get_clear_price(low)
            median = get_clear_price(median)

            price = (low + median) / 2

            price = (price + all_items[name])/2

            all_items[name] = price

            if price <= price_for_update:
                update_list.append(name)

            print('has been updated v')
            print(name, all_items[name])

        time.sleep(random.uniform(4, 5.5))

        del nameq, low, median, url, myreq, name

    global update
    update = False

def get_check():
    id = get('%s/itemdb/current_%s.json'%(mainlink,appid))['db']
    prices = requests.get('%s/itemdb/%s' %(mainlink,id))

    #print('second thread')

    for element in prices.text.split('\n')[1:-1:]:
        element = element.split(';')
        name = element[10].replace('"', '').strip()
        price = int(element[2])/100

        # на всякий случай ибо вдруг у нас нет предмета на стиме но есть на тме -_-
        if all_items.get(name)!=None:
            thispercent = all_items[name]/price

            if thispercent >= needpercent and price >= minprice*100:
                info = json.loads(
                    requests.get(mainlink + '/api/ItemInfo/%s_%s/ru/?key=%s' % (element[0], element[1], secretKey)).text)
                if all_items[name] / (float(info['min_price']) / 100) > needpercent:
                    for item_in_count in range(int(info['offers'][0]['count'])):

                        buyit = requests.get(mainlink + '/api/Buy/%s_%s/%s/%s/?key=%s' % (
                        info['classid'], info['instanceid'], info['min_price'], info['hash'], secretKey)).text

                        buyit = json.loads(buyit)
                        if buyit['result'] == 'ok':
                            print(
                                '==================================== BOUGHT ====================================')
                            print(buyit)
                            print('Sell your item - %s for %sp. in steam market.' % (name, (float(element[2]) / 100) * needpercent))
                        else:
                            print('im sorry but you have not enough money for bying this item - %s:%f' % (name, price))
                        time.sleep(0.25)

    #time.sleep(1)

def main():
    print('started')
    total = 1
    now = 0
    names = []

    get_proxy()

    while now <= total:
        returned, total = parse_all_names(now)
        names.extend(returned)
        now += take_count

    #------------------------------------------ тут временное решение было касательно итемов стима
    for name in names:
        print(name)
        all_items.update(get_steam_price(name))

    del total, now, names

    last_time = time.time()-minutes_for_update*60
    print(last_time)
    print(time.time())

    global update

    while True:
        if (time.time() >= last_time+minutes_for_update*60) and not update:

            update = True

            threading.Thread(target=get_update).start()
            threading.Thread(target=get_proxy).start()

            last_time = time.time()

        # в любом случае запустить это

        t1 = threading.Thread(target=get_check)
        t1.start()
        t1.join()

if __name__ == '__main__':
    main()
