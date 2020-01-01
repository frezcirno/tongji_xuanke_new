#!/usr/bin/env python
# coding:utf-8
import os
import time
import json
import logging
import requests
from bs4 import BeautifulSoup
from base64 import b64encode
from fuzzywuzzy import fuzz
from urllib.parse import parse_qsl, urlsplit


class xuanke1(object):
    objSession = requests.Session()
    # objSession.proxies = {'http': '127.0.0.1:8888'}
    objSession.headers.update(
        {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:60.0) Gecko/20100101 Firefox/60.0'})
    __baseUrl = 'http://1.tongji.edu.cn'

    def __init__(self, id, password):
        res = login1(id, password, self.objSession)
        self.uid = res['uid']
        self.token = res['token']

        _, loginInfo = self.__login(self.token, self.uid)
        loginUser = loginInfo['user']
        self.type = loginUser['type']

        _, roundInfoList = self.getRounds()
        if len(roundInfoList) == 0:
            self.roundId = input('提示: 当前选课没有开放, 可以手动输入选课轮次ID: ')  # 4973
        elif len(roundInfoList) == 1:
            roundInfo = roundInfoList[0]
            self.roundId = roundInfo['id']
        else:
            for roundInfo in enumerate(roundInfoList):
                print(roundInfo['id'], '->',
                      roundInfo['calendarName'], roundInfo['name'])
                print('remark =', roundInfo['remark'])
            self.roundId = input('请选择选课轮次ID: ')

        print('RoundId ->', self.roundId)

    def __login(self, token, uid):
        '''登录获取sessionId'''
        return self.post('/api/sessionservice/session/login',
                         data={'token': token, 'uid': uid})

    def __request(self, method, url, params=None, data=None):
        info = [method, url]
        if params:
            info.append('with params =')
            info.append(params)
        if data:
            info.append('with data =')
            info.append(data)
        logging.info(info)
        res = self.objSession.request(method, self.__baseUrl+url,
                                      params=params, data=data)
        resjson = res.json()
        if not res.status_code == 200:
            logging.warning([res.status_code, resjson['message']])
            return res.status_code, resjson['message']
        return resjson['code'], resjson['data']

    def post(self, url, params=None, data=None):
        return self.__request('post', url, params, data)

    def get(self, url, params=None):
        return self.__request('get', url, params)

    def currentTermCalendar(self):
        '''获取当前学期信息'''
        return self.get('/api/baseresservice/schoolCalendar/currentTermCalendar',
                        {'_t': timestamp()})

    def schoolCalendar(self):
        return self.get('/api/baseresservice/schoolCalendar/list', params={'_t': timestamp()})

    def findUserInfoByIdType(self, uid=None, type=None):
        '''获取学生信息(详细版)'''
        if uid is None:
            uid = self.uid
        if type is None:
            type = self.type
        return self.get('/api/studentservice/studentInfo/findUserInfoByIdType',
                        params={
                            'userId': b64encode(uid.encode('utf-8')),
                            'type': b64encode(type.encode('utf-8')),
                            '_t': timestamp()
                        })

    def findUserInfoByType(self, uid=None, type=None):
        '''获取学生信息(简短版)'''
        if uid is None:
            uid = self.uid
        if type is None:
            type = self.type
        return self.get('/api/studentservice/studentInfo/findUserInfoByType',
                        params={
                            'userId': b64encode(uid.encode('utf-8')),
                            'type': b64encode(type.encode('utf-8')),
                            '_t': timestamp()
                        })

    def getRounds(self, projectId=1):
        '''获取选课开放信息'''
        return self.post('/api/electionservice/student/getRounds',
                         params={'projectId': projectId})

    def loginCheck(self, uid=None):
        '''检查是否登录成功, 选课前可以调用, status=Init说明OK'''
        if uid is None:
            uid = self.uid
        return self.post('/api/electionservice/student/loginCheck', data={
            'roundId': self.roundId,
            'studentId': uid
        })

    def loading(self):
        '''loading的时候调用了这个方法, 响应的status=Ready的时候说明OK'''
        return self.post('/api/electionservice/student/' +
                         str(self.roundId) + '/loading')

    def electRes(self):
        '''轮询选课状态, 响应的status=Processing的时候等待, 为Ready的时候说明完毕, 返回结果'''
        return self.post('/api/electionservice/student/' +
                         str(self.roundId) + '/electRes')

    def getDataBk(self, useLocal=False):
        '''获取个人全部课表信息, 包括已修课程、计划课程、公共选修课、已选课程、正在学的课程等等'''
        if useLocal:
            try:
                with open('lastSucc.json', mode='r') as localDataFile:
                    localDataBk = json.load(localDataFile)
                return (200, localDataBk)
            except IOError:
                print('本地数据源获取失败, 使用网络源')

        res = self.post(
            '/api/electionservice/student/' + str(self.roundId) + '/getDataBk')
        if res[0] == 200:
            with open('lastSucc.json', mode='w') as file:  # 本地保存一下
                json.dump(res[0], file)
        return res

    def getTeachClass4Limit(self, courseCode):
        '''获取课程开班情况(包括已选人数等), courseCode为6位课程代码'''
        return self.post('/api/electionservice/student/getTeachClass4Limit', params={
            'roundId': self.roundId,
            'courseCode': courseCode,
            'studentId': self.uid
        })

    def getStuInfoByParam(self, uid=None):
        '''获取学籍信息(专业等)'''
        if uid is None:
            uid = self.uid
        return self.get('/api/studentservice/studentDetailInfo/getStuInfoByParam', params={
            'studentId': uid,
            'stuInfoClass': '学籍信息',
            '_t': timestamp()
        })

    def findCampusProfessionList(self, grade, keyWord):
        '''获取学院设立专业的列表'''
        return self.post('/api/commonservice/campusProfession/findCampusProfessionList', data={
            'grade': grade,
            'keyWord': keyWord,
            'pageSize_': 1,
            'pageNum_': 1
        })

    def getMajorCourseList(self, majorCode, grade, calendarId):
        '''获取专业课表'''
        return self.get('/api/arrangementservice/timetable/major', params={
            'code': majorCode,  # 专业代码
            'grade': grade,  # 入学年份
            'calendarId': calendarId,  # 年份
            '_t': timestamp()
        })

    def findHomePageCommonMsgPublish(self, pageNum=1, pageSize=20):
        '''获取系统公告'''
        return self.post('/api/commonservice/commonMsgPublish/findHomePageCommonMsgPublish', data={
            'pageNum_': pageNum,
            'pageSize_': pageSize
        })

    def studentPlanCountByStuId(self, uid=None):
        '''获取个人培养计划(各部分学分数)'''
        if uid is None:
            uid = self.uid
        return self.get('/api/cultureservice/culturePlan/studentPlanCountByStuId', params={'studentId': uid})

    def elect(self, courseList, withdrawClassList=[]):
        '''选课, 参数格式如下
        {
            'courseCode': 123456,  # 课程编号
            'courseName': 'xxxxxxx',  # 课程名
            'teachClassCode': 12345601,  # 班级编号
            'teachClassId': 111111112483123,  # 班级ID
            'teacherName': 'xx'  # 教师名
        }'''
        return self.post('/api/electionservice/student/elect', data=json.dumps({
            'roundId': self.roundId,
            'elecClassList': courseList,
            'withdrawClassList': withdrawClassList
        }))

    def findStudentTimetab(self, calendarId=None, uid=None):
        '''个人课表'''
        if uid is None:
            uid = self.uid
        if calendarId is None:
            _, calendarInfo = self.currentTermCalendar()
            calendarId = calendarInfo['schoolCalendar']['id']

        return self.get('/api/electionservice/reportManagement/findStudentTimetab', params={
            'calendarId': calendarId,
            'studentCode': uid,
            '_t': timestamp()
        })

    def findCourseInfoByCode(self, courseCode):
        '''查询某课程开班信息'''
        _, dataBk = self.getDataBk(useLocal=True)
        for plan in dataBk['planCourses']:
            if plan['courseCode'] == courseCode:
                return plan['course']
        for public in dataBk['publicCourses']:
            courseInfo = public['course']
            if courseInfo['courseCode'] == courseCode:
                return courseInfo
        return {}

    def findAllCourseInfoListByName(self, courseName: str):
        '''查询某课程开班信息'''
        res = []
        _, dataBk = self.getDataBk(useLocal=True)
        for plan in dataBk['planCourses']:
            courseInfo = plan['course']
            if courseInfo['courseName'].find(courseName) >= 0 or fuzz.ratio(courseInfo['courseName'], courseName) >= 30:
                res.append(courseInfo)
        for public in dataBk['publicCourses']:
            courseInfo = public['course']
            if courseInfo['courseName'].find(courseName) >= 0 or fuzz.ratio(courseInfo['courseName'], courseName) >= 30:
                res.append(courseInfo)
        return res


def login1(username, password, session):
    res = session.get('http://1.tongji.edu.cn:30100/oiosaml/saml/login')
    soup = BeautifulSoup(res.content, 'html.parser')
    res = session.get(soup.meta['content'][6:])
    if res.status_code != 200:
        return False

    res = session.post('https://ids.tongji.edu.cn:8443/nidp/saml2/sso?sid=0&sid=0', data={
        'option': 'credential',
        'Ecom_User_ID': username,
        'Ecom_Password': password
    })
    if res.status_code != 200:
        return False

    res = session.get('https://ids.tongji.edu.cn:8443/nidp/saml2/sso?sid=0')
    if res.status_code != 200:
        return False
    soup = BeautifulSoup(res.content, 'html.parser')
    res = session.post('http://1.tongji.edu.cn:30100/oiosaml/saml/SAMLAssertionConsumer',
                       data={'SAMLResponse': soup.input['value']})
    if res.status_code != 200:
        return False
    return dict(parse_qsl(urlsplit(res.url).query))  # 参数返回


def timestamp():  # 时间戳
    return str(int(time.time() * 1000))


def chooseClass(xuankewang: xuanke1, courseCode):
    _, classInfoList = xuankewang.getTeachClass4Limit(courseCode)
    for classInfo in classInfoList:
        print(classInfo['teachClassCode'], '->',  classInfo['campusI18n'],
              classInfo['teacherName'], classInfo['remark'],
              [time['timeAndRoom'] for time in classInfo['timeTableList']])
    teachClassCode = input('请输入你想选的班级的序号: ')
    classInfo = [
        eachClass for eachClass in classInfoList if eachClass['teachClassCode'] == teachClassCode][0]
    print('您选择了<<%s>> <<%s>>老师的<<%s>>' % (classInfo['campusI18n'],
                                          classInfo['teacherName'], classInfo['courseName']))
    print('请仔细检查选课要求 ->', classInfo['remark'])
    print('和课程时间 ->', [time['timeAndRoom']
                       for time in classInfo['timeTableList']])
    print('**确保课程不会冲突**')
    return classInfo


def chooseCourseAndClass(xuankewang: xuanke1):
    inputline = input('请输入课程名/课程代码(6位)/班级代码(8位): ')
    if len(inputline) == 6 or len(inputline) == 8:
        try:
            int(inputline)
            isCode = True
        except ValueError:
            isCode = False
    else:
        isCode = False

    if isCode:
        courseInfo = xuankewang.findCourseInfoByCode(inputline[:6])
        if not courseInfo:
            print('找不到课号为', inputline, '的课程')
            return {}
    else:
        courseInfoList = xuankewang.findAllCourseInfoListByName(
            inputline)
        if not courseInfoList:
            print('找不到名字为', inputline, '的课程')
            return {}
        for index, courseInfo in enumerate(courseInfoList):
            print(index, '->',  courseInfo['courseName'],
                  courseInfo['campus'], courseInfo['remark'])
        index = int(input('选择课程序号(-1取消): '))
        if index == -1:
            return {}
        courseInfo = courseInfoList[index]

    courseCode = courseInfo['courseCode']
    _, classInfoList = xuankewang.getTeachClass4Limit(courseCode)

    if isCode and len(inputline) == 8:
        classInfo = [
            eachClass for eachClass in classInfoList if eachClass['teachClassCode'] == inputline][0]
    else:
        for classInfo in classInfoList:
            print(classInfo['teachClassCode'], '->',  classInfo['campusI18n'],
                  classInfo['teacherName'], classInfo['remark'],
                  [time['timeAndRoom'] for time in classInfo['timeTableList']])
        teachClassCode = input('请输入你想选的班级的序号: ')
        classInfo = [
            eachClass for eachClass in classInfoList if eachClass['teachClassCode'] == teachClassCode][0]

    print('您选择了<<%s>> <<%s>>老师的<<%s>>' % (classInfo['campusI18n'],
                                          classInfo['teacherName'], classInfo['courseName']))
    print('请仔细检查选课要求 ->', classInfo['remark'])
    print('和课程时间 ->', [time['timeAndRoom']
                       for time in classInfo['timeTableList']])
    print('**确保课程不会冲突**')
    print()
    return classInfo


def main():
    logging.basicConfig(filename='xuanke1.log', level=logging.INFO)
    logging.info(['Running at', timestamp()])

    xuankewang = xuanke1(input('请输入学号: '), input('请输入密码: '))

    wishList = []
    withdrawList = []
    while True:
        print('当前抢课列表: ')
        for index, courseReq in enumerate(wishList):
            print(index, '->', courseReq['teachClassCode'],
                  courseReq['courseName'], courseReq['teacherName'])
        print('当前退课列表: ')
        for index, courseReq in enumerate(withdrawList):
            print(index, '->', courseReq['teachClassCode'],
                  courseReq['courseName'], courseReq['teacherName'])
        op = input('>>> ')
        if op == 'c':  # 查看我的课表
            _, myTimeTab = xuankewang.findStudentTimetab()
            for course in myTimeTab:
                print(course['courseName'], course['teacherName'], course['credits'],
                      course['classRoomI18n'], course['classTime'], course['remark'])
        elif op == 'cc':  # 查看我的课表
            _, schoolCalendar = xuankewang.schoolCalendar()
            for term in schoolCalendar:
                print(term['id'], '->', term['fullName'])
            termId = input('输入学期编号: ')
            _, myTimeTab = xuankewang.findStudentTimetab(calendarId=termId)
            for course in myTimeTab:
                print(course['courseName'], course['teacherName'], course['credits'],
                      course['classRoomI18n'], course['classTime'], course['remark'])
        elif op == 'a' or op == 'add':  # 添加要抢的课
            classInfo = chooseCourseAndClass(xuankewang)
            wishList.append({
                'courseCode': classInfo['courseCode'],  # 课程编号
                'courseName': classInfo['courseName'],  # 课程名
                'teachClassCode': classInfo['teachClassCode'],  # 班级编号
                'teachClassId': classInfo['teachClassId'],  # 班级ID
                'teacherName': classInfo['teacherName']  # 教师名
            })
        elif op == 'd' or op == 'delete':
            index = int(input('选择要删除的课程序号(-1取消): '))
            if 0 <= index < len(wishList):
                wishList.pop(index)
        elif op == 'wa' or op == 'withdraw add':
            classInfo = chooseCourseAndClass(xuankewang)
            withdrawList.append({
                'courseCode': classInfo['courseCode'],  # 课程编号
                'courseName': classInfo['courseName'],  # 课程名
                'teachClassCode': classInfo['teachClassCode'],  # 班级编号
                'teachClassId': classInfo['teachClassId'],  # 班级ID
                'teacherName': classInfo['teacherName']  # 教师名
            })
        elif op == 'wd' or op == 'withdraw delete':  # 添加要抢的课
            index = int(input('选择要删除的课程序号(-1取消): '))
            if 0 <= index < len(withdrawList):
                withdrawList.pop(index)
        elif op == 'e' or op == 'export':
            filename = input('输入导出文件名: ')
            with open(filename, mode='w') as f:
                json.dump(
                    {'wishList': wishList, 'withdrawList': withdrawList}, f)
            print('导出完毕')
        elif op == 'i' or op == 'import':
            filename = input('输入导入文件名: ')
            with open(filename, mode='r') as f:
                list = json.load(f)
                wishList = list['wishList']
                withdrawList = list['withdrawList']
            print('导入完毕')
        elif op == 's' or op == 'start':
            try:
                tryElectTimes = 0  # 选课请求次数
                while len(wishList) > 0:
                    successCoursesList = []
                    tryElectTimes += 1
                    print('Elect Request #', tryElectTimes)
                    code, _ = xuankewang.elect(wishList, withdrawList)
                    if not code == 200:
                        logging.warning('elect request failed')
                        print(code, '选课请求失败, 请检查账号密码以及网络')
                        break
                    tryGetStatusTimes = 0
                    while tryGetStatusTimes < 10:
                        tryGetStatusTimes += 1
                        _, electRes = xuankewang.electRes()
                        print(tryGetStatusTimes, electRes['status'])
                        if electRes['status'] == 'Ready':
                            successCoursesList = electRes['successCourses']
                            if successCoursesList:
                                logging.info(
                                    ['success ->', successCoursesList])
                                print('success ->', successCoursesList)
                            if electRes['failedReasons']:
                                logging.warning(
                                    ['failedReasons ->', electRes['failedReasons']])
                                print(electRes['failedReasons'])
                            break
                        time.sleep(1)
                    wishList = [courseReq for courseReq in wishList
                                if not successCoursesList.count(courseReq['teachClassId'])]
                    withdrawList = [courseReq for courseReq in withdrawList
                                    if not successCoursesList.count(courseReq['teachClassId'])]
            except KeyboardInterrupt:
                print('检测到键盘终止')
        elif op == 'q' or op == 'quit':
            print('GoodBye')
            break
        else:
            print('未知操作 ->', op)
            print('"c" -> 查看我的课表')
            print('"cc" -> 查询历史课表')
            print('"a"|"add" -> 添加要抢的课')
            print('"d"|"delete" -> 删除要抢的课')
            print('"wa"|"withdraw add" -> 添加要退的课')
            print('"wd"|"withdraw delete" -> 删除要退的课')
            print('"e"|"export" -> 导出抢/退课列表')
            print('"i"|"import" -> 导入抢/退课列表')
            print('"s"|"start" -> 开始抢课')
            print('"h"|"help" -> 提示信息')
            print('"q"|"quit" -> 退出')
            continue


if __name__ == '__main__':
    main()
