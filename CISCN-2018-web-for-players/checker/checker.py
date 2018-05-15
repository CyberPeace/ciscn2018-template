import re
import sys
import requests as req
from pyquery import PyQuery as PQ
import string
import random
import re

'''
route list

login:      /login
register:   /register
logout:     /logout
reset pass:  /pass/reset
change pass: /user/change
user info:   /user
commodity list: /shop
commodity info: /info/(id)
pay: /pay
second kill: /seckill
shopping car: /shopcar
shop car add: /shopcar/add
captcha:    /captcha
'''

class WebChecker:
    def __init__(self, ip, port, csrfname = '_xsrf'):
        self.ip = ip
        self.port = port
        self.url = 'http://%s:%s/' % (ip, port)
        self.username = '4uuu'
        self.password = '123456'
        self.change_pass = '654321'
        self.mail = 'i@qvq.im'
        self.csrfname = csrfname
        self.integral = None
        self.session = req.session()
    
    def _generate_randstr(self, len = 10):
        return ''.join(random.sample(string.ascii_letters, len))

    def _get_uuid(self):
        res = self.session.get(self.url + 'login')
        dom = PQ(res.text)
        return dom('form canvas').attr('rel')

    def _get_answer(self):
        uuid = self._get_uuid()
        answer = {}
        with open('./ans/ans%s.txt' % uuid, 'r') as f:
            for line in f.readlines():
                if line != '\n':
                    ans = line.strip().split('=')
                    answer[ans[0].strip()] = ans[1].strip()
        x = random.randint(int(float(answer['ans_pos_x_1'])), int(float(answer['ans_width_x_1']) + float(answer['ans_pos_x_1'])))
        y = random.randint(int(float(answer['ans_pos_y_1'])), int(float(answer['ans_height_y_1']) + float(answer['ans_pos_y_1'])))
        return x,y

    def _get_user_integral(self):
        res = self.session.get(self.url + 'user')
        dom = PQ(res.text)
        res = dom('div.user-info').text()
        integral = re.search('(\d+\.\d+)', res).group()
        return integral

    def _get_token(self, html):
        dom = PQ(html)
        form = dom("form")
        token = str(PQ(form)("input[name=\"%s\"]" % self.csrfname).attr("value")).strip()
        return token

    def login_test(self):
        rs = self.session.get(self.url + 'login')
        token = self._get_token(rs.text)
        x,y = self._get_answer()
        rs = self.session.post(url=self.url + 'login', data={
            self.csrfname: token,
            "username": self.username,
            "password": self.password,
            "captcha_x": x,
            "captcha_y": y
        })
        try:
            dom = PQ(rs.text)
            error = dom("div.alert.alert-danger")
            error = PQ(error).text().strip()
            if len(error):
                print "[-] Login failed."
                return False
        except:
            pass
        print "[+] Login Success."
        return True

    def register_test(self, invite = ''):
        rs = self.session.get(self.url + 'register')
        token = self._get_token(rs.text)
        x,y = self._get_answer()
        rs = self.session.post(url=self.url + 'register', data={
            self.csrfname: token,
            "username": self.username,
            "password": self.password,
            "password_confirm": self.password,
            "mail": self.mail,
            "invite_user": invite,
            "captcha_x": x,
            "captcha_y": y,
        })
        try:
            dom = PQ(rs.text)
            error = dom("div.alert.alert-danger")
            error = PQ(error).text().strip()
            if len(error):
                print "[-] Register failed."
                return False
        except:
            pass
        print "[+] Register Success."
        return True

    def invite_test(self):
        integral = self._get_user_integral()
        iv = req.session()
        res = iv.get(self.url + 'register')
        token = self._get_token(res.text)
        password = self._generate_randstr(10)
        x,y = self._get_answer()
        res = iv.post(url=self.url + 'register', data={
            self.csrfname: token,
            "username": self._generate_randstr(6),
            "password": password,
            "password_confirm": password,
            "mail": self._generate_randstr(5) + '@qvq.im',
            "invite_user": self.username,
            "captcha_x": x,
            "captcha_y": y
        })
        new_integral = self._get_user_integral()
        if new_integral != integral:
            print '[+] Invite Success'
            return True
        print '[-] Invite Failed'
        return False

    def change_password_test(self):
        rs = self.session.get(self.url + 'user/change')
        token = self._get_token(rs.text)
        res = self.session.post(self.url + 'user/change', data={
            self.csrfname: token,
            "old_password": self.password,
            "password": self.change_pass,
            "password_confirm": self.change_pass
        })
        dom = PQ(res.text)
        success = dom('div.alert.alert-success')
        success = PQ(success).text().strip()
        if len(success):
            newPass = req.session()
            rs = newPass.get(self.url + 'login')
            new_token = self._get_token(rs.text)
            x,y = self._get_answer()
            rs = newPass.post(url=self.url + 'login', data={
                self.csrfname: new_token,
                "username": self.username,
                "password": self.change_pass,
                "captcha_x": x,
                "captcha_y": y
            })
            try:
                dom = PQ(rs.text)
                error = dom("div.alert.alert-danger")
                error = PQ(error).text().strip()
                if len(error):
                    print '[-] Change Password Failed'
                    return False
            except:
                pass
            print '[+] Change Password Success'
            return True
        print '[-] Change Password Failed'
        return False

    def reset_password_test(self):
        res = self.session.get(self.url + 'pass/reset')
        token = self._get_token(res.text)
        x,y = self._get_answer()
        rs = self.session.post(self.url + 'pass/reset', data={
            self.csrfname: token,
            'mail': self.mail,
            "captcha_x": x,
            "captcha_y": y
        })
        dom = PQ(rs.text)
        failed = dom('div.alert.alert-danger')
        failed = PQ(failed).text().strip()
        if len(failed):
            print '[-] Reset Password Failed'
            return True
        print '[+] Reset Password Success'
        return False

    def commodity_test(self):
        rs = self.session.get(self.url + 'shop')
        dom = PQ(rs.text)
        list = dom('div.commodity-list').text().strip()
        if len(list):
            print "[+] Commodity list Success"
            return True
        else:
            print "[-] Commodity list Failed."
            return False
        
    def pay_test(self):
        integral = self._get_user_integral()
        rs = self.session.get(self.url + 'info/1')
        token = self._get_token(rs.text)
        rs = self.session.post(self.url + 'pay', data={
            self.csrfname: token,
            'price': float(random.randint(1, 50))
        })
        new_integral = self._get_user_integral()
        if float(new_integral) < float(integral):
            print '[+] Pay Success'
            return True
        print '[-] Pay Failed'
        return False

    def _get_amount(self, id):
        res = self.session.get(self.url + 'info/%s' % str(id))
        dom = PQ(res.text)
        res = dom('div.commodity-info').text()
        text = re.search('Amount: (\d+)', res).group()
        return re.search('(\d+)', text).group()

    def second_kill_test(self):
        amount = self._get_amount('2')
        rs = self.session.get(self.url + 'seckill')
        token = self._get_token(rs.text)
        self.session.post(self.url + 'seckill', data={
            self.csrfname: token,
            'id': 2
        })
        new_amount = self._get_amount('2')
        if int(new_amount) < int(amount):
            print '[+] Second Kill Success'
            return True
        else:
            print '[-] Second Kill Failed'
            return False

    def shopcar_pay_test(self):
        integral = self._get_user_integral()
        rs = self.session.get(self.url + 'shopcar')
        token = self._get_token(rs.text)
        rs = self.session.post(self.url + 'shopcar', data={
            self.csrfname: token,
            'price': float(random.randint(1,50))
        })
        new_integral = self._get_user_integral()
        if float(new_integral) < float(integral):
            print '[+] Shopcar Pay Success'
            return True
        print '[-] Shopcar Pay Failed'
        return False
    
    def shopcar_add_test(self):
        rs = self.session.get(self.url + 'shop')
        dom = PQ(rs.text)
        form = dom("form")
        token = str(PQ(form[0])("input[name=\"%s\"]" % self.csrfname).attr("value")).strip()
        rs = self.session.post(self.url + 'shopcar/add', data={
            self.csrfname: token,
            'id': 1
        })
        dom = PQ(rs.text)
        commodity = dom('div.shopcar_list')
        commodity = PQ(commodity).text().strip()
        if len(commodity):
            print '[+] Shopcar Add Success'
            return True
        print '[-] Shopcar Add Failed'
        return False


def checker(ip, port, csrfname):
    try:
        check = WebChecker(str(ip), str(port), csrfname)
        check.register_test()
        check.login_test()
        check.commodity_test()
        check.invite_test()
        check.pay_test()
        check.change_password_test()
        check.reset_password_test()
        check.second_kill_test()
        check.shopcar_add_test()
        check.shopcar_pay_test() 
        print '[-] Done'
    except Exception as ex:
        return '[!] Error, Unknown Exception,' + str(ex)

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Wrong Params")
        print("example: python %s %s %s %s" % (sys.argv[0], '127.0.0.1', '80', '_xsrf'))
        exit(0)
    ip = sys.argv[1]
    port = sys.argv[2]
    csrfname = sys.argv[3]
    print(checker(ip, port, csrfname))