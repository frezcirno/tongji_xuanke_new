#!/usr/bin/env python
# coding:utf-8
import re
import json
import logging
import requests
import functools
from time import time
from bs4 import BeautifulSoup
from base64 import b64encode
from fuzzywuzzy import fuzz
from urllib.parse import parse_qsl, urlsplit

logging.basicConfig(filename='api.log', level=logging.INFO)


def timestamp():  # 时间戳
    return str(int(time() * 1000))


def request(session, method, url, params=None, data=None):
    '''记录Log的Request'''
    logging.info(method+url+str(params)+str(data))
    return session.request(method, url, params=params, data=data)


def post(session, url, params=None, data=None):
    return request(session, 'post', url, params, data)


def get(session, url, params=None):
    return request(session, 'get', url, params)


def ssoRequest(session, username, password):
    '''返回SAMLResponse'''
    res = post(session, 'https://ids.tongji.edu.cn:8443/nidp/saml2/sso?sid=0&sid=0', data={
        'option': 'credential',
        'Ecom_User_ID': username,
        'Ecom_Password': password
    })
    url = re.search(r"href=\'(.*?)\'", res.text).group(1)
    res = get(session, url)
    try:
        return re.search(r'value="(.*?)"', res.text).group(1)
    except:
        return ''


def json_api(func):
    @functools.wraps(func)
    def wrapper(*args, **kw):
        res = func(*args, **kw)
        try:
            api_res = res.json()
            if 'message' in api_res:
                print('服务器错误', api_res['message'])
            return api_res['data']
        except (ValueError, KeyError):
            return None
    return wrapper


class xuanke1(object):
    __host = 'http://1.tongji.edu.cn'
    __shost = 'https://1.tongji.edu.cn'

    def __init__(self):
        self.s = requests.Session()
        self.s.headers.update(
            {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:60.0) Gecko/20100101 Firefox/60.0'})
        self.uid = ''
        self.password = ''
        self.token = ''
        self.user = {}
        self.roundId = 0

    def __ssoLogin(self, username, password):
        try:
            res = get(self.s, 'http://1.tongji.edu.cn:30100/oiosaml/saml/login')
            urlrequ = re.search(r'url=(.*?)"', res.text).group(1)
            res = get(self.s, urlrequ)
            resp = ssoRequest(self.s, username, password)
            if not resp:
                print('密码错误')
                return {}
            res = post(self.s, 'http://1.tongji.edu.cn:30100/oiosaml/saml/SAMLAssertionConsumer',
                       data={'SAMLResponse': resp})  # 这里会跳转两次
            return dict(parse_qsl(urlsplit(res.url).query))  # 参数返回
        except Exception as e:
            return {'Exception': e}

    @json_api
    def login(self, uid, password):
        '''登录获取sessionId'''
        if not self.token:
            if self.token:
                self.logout()
            ticket = self.__ssoLogin(uid, password)
            if 'uid' in ticket:
                self.uid = ticket['uid']
            if 'token' in ticket:
                self.token = ticket['token']
            self.password = password

        res = post(self.s, xuanke1.__shost+'/api/sessionservice/session/login',
                   data={'uid': self.uid, 'token': self.token})

        return res

    def logout(self):
        post(self.s, xuanke1.__shost+'/api/sessionservice/session/logout',
             data={
                 'uid': self.uid,
                 'sessionid': self.s.cookies.get('sessionid')
             })
        return get(self.s, 'http://1.tongji.edu.cn:30100/oiosaml/saml/Logout')

    def _login4m3(self, username, password):
        try:
            res = get(self.s,
                      'http://4m3.tongji.edu.cn/eams/samlCheck')
            req = re.search(r'url=(.*?)"', res.text).group(1)
            get(self.s, req)
            resp = ssoRequest(self.s, username, password)
            res = post(self.s, 'http://4m3.tongji.edu.cn/eams/saml/SAMLAssertionConsumer',
                       data={'SAMLResponse': resp})
            return True
        except:
            return False

    @json_api
    def currentTermCalendar(self):
        '''获取当前学期信息'''
        return get(self.s, xuanke1.__host+'/api/baseresservice/schoolCalendar/currentTermCalendar',
                   {'_t': timestamp()})

    @json_api
    def schoolCalendar(self):
        return get(self.s, xuanke1.__host+'/api/baseresservice/schoolCalendar/list', params={'_t': timestamp()})

    @json_api
    def findUserInfoByIdType(self, uid=None, type=None):
        '''获取学生信息(详细版)'''
        if uid is None:
            uid = str(self.uid)
        if type is None:
            type = str(self.user['type'])
        return get(self.s, xuanke1.__host+'/api/studentservice/studentInfo/findUserInfoByIdType',
                   params={
                       'userId': b64encode(uid.encode('utf-8')),
                       'type': b64encode(type.encode('utf-8')),
                       '_t': timestamp()
                   })

    @json_api
    def findUserInfoByType(self, uid=None, type=None):
        '''获取学生信息(简短版)'''
        if uid is None:
            uid = str(self.uid)
        if type is None:
            type = str(self.user['type'])
        return get(self.s, xuanke1.__host+'/api/studentservice/studentInfo/findUserInfoByType',
                   params={
                       'userId': b64encode(uid.encode('utf-8')),
                       'type': b64encode(type.encode('utf-8')),
                       '_t': timestamp()
                   })

    @json_api
    def myTutor(self):
        return get(self.s, xuanke1.__host+'/api/welcomeservice/tutorStudent/myTutor', params={
            'type': 2,
            '_t': timestamp()
        })

    @json_api
    def getRounds(self, projectId=1):
        '''获取选课开放信息'''
        return post(self.s, xuanke1.__shost+'/api/electionservice/student/getRounds',
                    params={'projectId': projectId})

    @json_api
    def loginCheck(self, uid=None):
        '''检查是否登录成功, 选课前可以调用, status=Init说明OK'''
        if uid is None:
            uid = self.uid
        return post(self.s, xuanke1.__host+'/api/electionservice/student/loginCheck', data={
            'roundId': self.roundId,
            'studentId': uid
        })

    @json_api
    def loading(self):
        '''loading的时候调用了这个方法, 响应的status=Ready的时候说明OK'''
        return post(self.s, xuanke1.__host+'/api/electionservice/student/' +
                    str(self.roundId)+'/loading')

    @json_api
    def electRes(self):
        '''轮询选课状态, 响应的status=Processing的时候等待, 为Ready的时候说明完毕, 返回结果'''
        return post(self.s, xuanke1.__host+'/api/electionservice/student/' +
                    str(self.roundId)+'/electRes')

    def getDataBk(self, allowCache=False):
        '''获取个人全部课表信息, 包括已修课程、计划课程、公共选修课、已选课程、正在学的课程等等
            返回类型: json
        '''
        if allowCache:
            try:
                with open('cache.json', mode='r') as localDataFile:
                    localDataBk = json.load(localDataFile)
                return localDataBk
            except IOError:
                print('本地数据源获取失败, 使用网络源')

        if not self.roundId:
            print('未指定选课轮次')
            return {}

        res = post(self.s,
                   xuanke1.__host+'/api/electionservice/student/'+str(self.roundId)+'/getDataBk')
        if res.ok():
            with open('cache.json', mode='w') as file:  # 如果获取成功, 本地保存一下
                json.dump(res.json(), file)
        return res.json()

    @json_api
    def getTeachClass4Limit(self, courseCode):
        '''获取课程开班情况(包括已选人数等), courseCode为6位课程代码'''
        return post(self.s, xuanke1.__host+'/api/electionservice/student/getTeachClass4Limit', params={
            'roundId': self.roundId,
            'courseCode': courseCode,
            'studentId': self.uid
        })

    @json_api
    def getStuInfoByParam(self, uid=None):
        '''获取学籍信息(专业等)'''
        if uid is None:
            uid = self.uid
        return get(self.s, xuanke1.__host+'/api/studentservice/studentDetailInfo/getStuInfoByParam', params={
            'studentId': uid,
            'stuInfoClass': '学籍信息',
            '_t': timestamp()
        })

    @json_api
    def findCampusProfessionList(self, grade, keyWord, pageSize=10, pageNum=1):
        '''获取学院设立专业的列表'''
        return post(self.s, xuanke1.__host+'/api/commonservice/campusProfession/findCampusProfessionList', data={
            'grade': grade,
            'keyWord': keyWord,
            'pageSize_': pageSize,
            'pageNum_': pageNum
        })

    @json_api
    def getMajorCourseList(self, majorCode, grade, calendarId):
        '''获取专业课表'''
        return get(self.s, xuanke1.__host+'/api/arrangementservice/timetable/major', params={
            'code': majorCode,  # 专业代码
            'grade': grade,  # 入学年份
            'calendarId': calendarId,  # 年份
            '_t': timestamp()
        })

    @json_api
    def findHomePageCommonMsgPublish(self, pageNum=1, pageSize=20):
        '''获取系统公告'''
        return post(self.s, xuanke1.__shost+'/api/commonservice/commonMsgPublish/findHomePageCommonMsgPublish', data={
            'pageNum_': pageNum,
            'pageSize_': pageSize
        })

    @json_api
    def studentPlanCountByStuId(self, uid=None):
        '''获取个人培养计划(各部分学分数)'''
        if uid is None:
            uid = self.uid
        return get(self.s, xuanke1.__host+'/api/cultureservice/culturePlan/studentPlanCountByStuId', params={'studentId': uid})

    @json_api
    def elect(self, courseList, withdrawClassList=[]):
        '''选课, 参数格式如下
        {
            'courseCode': 123456,  # 课程编号
            'courseName': 'xxxxxxx',  # 课程名
            'teachClassCode': 12345601,  # 班级编号
            'teachClassId': 111111112483123,  # 班级ID
            'teacherName': 'xx'  # 教师名
        }'''
        return post(self.s, xuanke1.__host+'/api/electionservice/student/elect', data=json.dumps({
            'roundId': self.roundId,
            'elecClassList': courseList,
            'withdrawClassList': withdrawClassList
        }))

    @json_api
    def findStudentTimetab(self, calendarId, uid=None):
        '''个人课表'''
        if uid is None:
            uid = self.uid
        return get(self.s, xuanke1.__host+'/api/electionservice/reportManagement/findStudentTimetab', params={
            'calendarId': calendarId,
            'studentCode': uid,
            '_t': timestamp()
        })

    def findCourseInfoByCode(self, courseCode):
        '''查询某课程开班信息'''
        dataBk = self.getDataBk(allowCache=True)
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
        dataBk = self.getDataBk(allowCache=True)
        for plan in dataBk['planCourses']:
            courseInfo = plan['course']
            if courseInfo['courseName'].find(courseName) >= 0 or fuzz.ratio(courseInfo['courseName'], courseName) >= 30:
                res.append(courseInfo)
        for public in dataBk['publicCourses']:
            courseInfo = public['course']
            if courseInfo['courseName'].find(courseName) >= 0 or fuzz.ratio(courseInfo['courseName'], courseName) >= 30:
                res.append(courseInfo)
        return res

    def chooseCourseAndClass(self):
        '''交互式地选择课程'''
        inputline = input(
            'Please input course name/course code(6 digits)/class code(8 digits): ')
        isCode = False
        if (len(inputline) == 6 or len(inputline) == 8) and inputline.isdigit():
            isCode = True

        '''获取课程信息'''
        if isCode:  # 课程代码 or 班级代码
            courseInfo = self.findCourseInfoByCode(inputline[:6])
            if not courseInfo:
                print('找不到课号为', inputline, '的课程')
                return {}
        else:
            courseInfoList = self.findAllCourseInfoListByName(
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

        '''获取班级列表'''
        courseCode = courseInfo['courseCode']
        classInfoList = self.getTeachClass4Limit(courseCode)

        '''选择班级'''
        if isCode and len(inputline) == 8:  # 若是班级代码直接选中
            classInfo = [
                eachClass for eachClass in classInfoList if eachClass['teachClassCode'] == inputline][0]
            if classInfo is None:
                return {}
        else:  # 否则询问
            for classInfo in classInfoList:
                print(classInfo['teachClassCode'], '->',  classInfo['campusI18n'],
                      classInfo['teacherName'], classInfo['remark'],
                      [time['timeAndRoom'] for time in classInfo['timeTableList']])
            teachClassCode = input('请输入你想选的班级的序号: ')
            classInfo = [
                eachClass for eachClass in classInfoList if eachClass['teachClassCode'] == teachClassCode][0]

        print('您选择了<<%s>> <<%s>>老师的<<%s>>' % (classInfo['campusI18n'],
                                              classInfo['teacherName'], classInfo['courseName']))
        print('选课要求 ->', classInfo['remark'])
        print('课程时间 ->', [time['timeAndRoom']
                          for time in classInfo['timeTableList']])
        print('Id ->', classInfo['teachClassId'])
        print('**请手动确保课程不会冲突**')
        return classInfo

    def chooseCalandarId(self):
        '''交互式地输入学期id'''
        schoolCalendar = self.schoolCalendar()

        for term in schoolCalendar:
            print(term['id'], '->', term['fullName'])

        termId = input('输入学期编号: ')
        if not termId:
            print('使用当前学期')
            calendarInfo = self.currentTermCalendar()
            termId = calendarInfo['schoolCalendar']['id']
        return termId
