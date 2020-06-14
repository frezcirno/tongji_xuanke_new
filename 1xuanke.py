#!/usr/bin/env python
# coding:utf-8

import json
import logging
from lxml import etree
from time import sleep
from api import xuanke1


logging.basicConfig(
    filename='lastrun.log',
    filemode='w',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


class Spider:
    def __init__(self):
        self.xuankewang = xuanke1()
        self.uid = ''
        self.password = ''
        self.electList = []
        self.withdrawList = []
        self.electTimePeriod = 1
        self.checkTimePeriod = 0.5
        self.errorTimePeriod = 1
        print('** 输入help查看提示信息')
        if self.login() == 0:
            self.round()
        self.help()

    def table(self, args):
        argc = len(args)
        termId = argc > 1 and args[1] or self.xuankewang.chooseCalandarId()
        uid = argc > 2 and args[2] or input(
            '输入学号: ') or self.xuankewang.uid
        myTimeTab = self.xuankewang.findStudentTimetab(termId, uid)
        totalCourseCount = 0
        totalCredits = 0
        for course in myTimeTab:
            totalCourseCount += 1
            totalCredits += float(course['credits'])
            print(course['courseName'], course['teacherName'], course['credits'],
                  course['classRoomI18n'], course['classTime'], course['remark'])
        print('一共%d门课%d学分' % (totalCourseCount, totalCredits))

    def info(self, args):
        def get1(uid):
            info = self.xuankewang.findUserInfoByIdType(uid)
            print(info['studentId'], info['name'], info['sexI18n'])
            print(info['facultyI18n'], info['professionI18n'],
                  info['grade'],  info['trainingLevelI18n'])
            # print('导师: ', info['teacherName'])

        argc = len(args)
        qList = argc > 1 and args[1:] or [input('输入学号: ')]
        if not qList[0]:
            qList = [self.xuankewang.uid]
        for query in qList:
            if query.find('-') != -1:
                uidRange = query.split('-')
                if len(uidRange) != 2 or not uidRange[0].isdigit() or not uidRange[1].isdigit():
                    print('输入有误')
                    return
                for uid in range(int(uidRange[0]), int(uidRange[1])):
                    get1(str(uid))
            else:
                get1(query)
            sleep(0.05)

    def msg(self):
        msgs = self.xuankewang.findHomePageCommonMsgPublish()
        for index, msg in enumerate(msgs['list']):
            print('-- 第%d个通知' % index)
            index += 1
            print('面向群体: ', msg['faceUserName'])
            print('标题: ', msg['title'])
            s = ''
            for piece in etree.HTML(msg['content']).xpath('//text()'):
                s += piece
            print(s)

    def course(self, args):
        argc = len(args)
        majorCode = argc > 1 and args[1] or input('输入专业代码: ')
        grade = argc > 2 and args[2] or input('输入年级: ')
        calendarId = argc > 3 and args[3] or self.xuankewang.chooseCalandarId()
        courseList = self.xuankewang.getMajorCourseList(
            majorCode, grade, calendarId)
        for course in courseList:
            print(course['value'])

    def major(self, args):
        argc = len(args)
        grade = argc > 1 and args[1] or input('输入年级: ')
        keyWord = argc > 2 and args[2] or input('输入学院名称: ')
        data = self.xuankewang.findCampusProfessionList(grade, keyWord)
        try:
            for majorInfo in data['list']:
                print(majorInfo['professionCode'], majorInfo['professionName'],
                      majorInfo['professionNameEn'], majorInfo['facultyI18n'])
        except KeyError:
            print('接口调用失败')

    def tutor(self):
        data = self.xuankewang.myTutor()
        print(data['teacherName'], data['introduce'])

    def add_list(self, args):
        classInfo = self.xuankewang.chooseCourseAndClass()
        if not classInfo:
            print('课程添加失败')
            return

        op = args[0]
        li = self.electList if op == 'add' or op == 'a' else self.withdrawList

        li.append({
            'courseCode': classInfo['courseCode'],  # 课程编号
            'courseName': classInfo['courseName'],  # 课程名
            'teachClassCode': classInfo['teachClassCode'],  # 班级编号
            'teachClassId': classInfo['teachClassId'],  # 班级ID
            'teacherName': classInfo['teacherName']  # 教师名
        })

    def rmv_list(self, args):
        argc = len(args)
        index = argc > 1 and int(args[1]) or int(
            input('选择要删除的课程序号(-1取消): '))

        op = args[0]
        li = self.electList if op == 'delete' or op == 'd' else self.withdrawList

        if 0 <= index < len(li):
            li.pop(index)
            print('删除成功！')

    def exportList(self, args):
        argc = len(args)
        filename = argc > 1 and args[1] or input(
            '输入导出文件名: ') or 'electList.json'
        with open(filename, mode='w') as f:
            json.dump(
                {'electList': self.electList, 'withdrawList': self.withdrawList}, f)
        print('导出完毕')

    def importList(self, args):
        argc = len(args)
        filename = argc > 1 and args[1] or input(
            '输入导入文件名: ') or 'electList.json'
        try:
            with open(filename, mode='r') as f:
                list = json.load(f)
                if 'electList' in list:
                    self.electList = list['electList']
                if 'withdrawList' in list:
                    self.withdrawList = list['withdrawList']
            print('导入完毕')
        except OSError as e:
            print(e.strerror, '文件打开失败')

    def login(self, args=[]):
        argc = len(args)
        self.uid = argc > 1 and args[1] or input('请输入学号: ')
        self.password = argc > 2 and args[2] or input('请输入密码: ')
        res = self.xuankewang.login(self.uid, self.password)
        if res:
            self.xuankewang.user = res['user']
            print('登录成功')
            return 0
        else:
            print('登陆失败, 账号或密码错误')
            return -1

    def round(self, args=[]):
        argc = len(args)
        self.xuankewang.roundId = argc > 1 and args[1]
        if not self.xuankewang.roundId:
            roundInfoList = self.xuankewang.getRounds()
            if len(roundInfoList) == 0:
                inputId = input('获取选课轮次失败, 可以手动输入选课轮次ID: ')
                if inputId:
                    self.xuankewang.roundId = int(inputId)  # 4973
            elif len(roundInfoList) == 1:
                roundInfo = roundInfoList[0]
                self.xuankewang.roundId = roundInfo['id']
            else:
                for roundInfo in roundInfoList:
                    print(roundInfo['id'], '->',
                          roundInfo['calendarName'], roundInfo['name'])
                    # print('remark =', roundInfo['remark'])
                self.xuankewang.roundId = int(input('请选择选课轮次ID: '))
        print('RoundId ->', self.xuankewang.roundId)

    def help(self, op=''):
        if op:
            print('未知操作 ->', op)
        print('l|login  [uid] [password]    -> 登录')
        print('r|round  [roundId]           -> 选择选课轮次')
        print('msg                          -> 获取 1.tongji 上的通知')
        print('info     [uid|uid1-uid2]     -> 查询学生信息')
        print('tutor                        -> 查询我的导师')
        print('major    [grade] [keyWord]   -> 查询开设专业信息')
        print('course   [majorCode] [grade] [calandarId] -> 查询专业课表')
        print('table    [calandarId] [uid]  -> 查看课表')
        print('f|fresh                      -> 更新课程数据')
        print('a|add                        -> 添加要抢的课')
        print('d|delete [index]             -> 删除要抢的课')
        print('wa|wadd                      -> 添加要退的课')
        print('wd|wdelete [index]           -> 删除要退的课')
        print('e|export [fileName]          -> 导出抢/退课列表')
        print('i|import [fileName]          -> 导入抢/退课列表')
        print('s|start                      -> 开始抢课')
        print('q|quit                       -> 退出')
        print('*                            -> 显示此提示信息')

    def book(self):
        try:
            classInfo = xuankewang.cuseCacheass()
            self.xuankewang._login4m3(
                self.xuankewang.uid, self.xuankewang.password)
            res = self.xuankewang.s.post('http://4m3.tongji.edu.cn/eams/courseTableForStd!searchTextbook.action', params={
                'lessonId': classInfo['teachClassId']
            })
            print(res.text)
        except:
            print('教材信息查询失败了')

    def start(self):
        try:
            tryElectTimes = 0  # 选课请求次数
            while len(self.electList):
                successCoursesList = []
                tryElectTimes += 1
                print('发送选课请求 #', tryElectTimes)
                msg = self.xuankewang.elect(self.electList, self.withdrawList)
                if not msg:
                    print('检查是否掉线...')
                    msg = self.xuankewang.loginCheck()
                    if msg['status'] != 'Init':
                        print('已掉线,重新登录中...')
                        self.xuankewang.login(self.uid, self.password)

                    for tryLoadingTimes in range(5):
                        print('加载中...', tryLoadingTimes)
                        data = self.xuankewang.loading()
                        if data['status'] == 'Ready':
                            break
                        sleep(1)
                    continue

                for tryGetStatusTimes in range(5):
                    electRes = self.xuankewang.electRes()
                    print(tryGetStatusTimes, electRes['status'])
                    if electRes['status'] == 'Ready':
                        successCoursesList = electRes['successCourses']
                        if successCoursesList:
                            newList = []
                            for courseReq in self.electList:
                                if courseReq['teachClassId'] in successCoursesList:
                                    print(courseReq['teachClassCode'],
                                          courseReq['courseName'], courseReq['teacherName'], '选课成功')
                                else:
                                    newList.append(courseReq)
                            self.electList = newList[:]
                            newList = []
                            for courseReq in self.withdrawList:
                                if courseReq['teachClassId'] in successCoursesList:
                                    print(courseReq['teachClassCode'],
                                          courseReq['courseName'], courseReq['teacherName'], '退课成功')
                                else:
                                    newList.append(courseReq)
                            withdrawList = newList[:]
                        if electRes['failedReasons']:
                            print(electRes['failedReasons'])
                        break
                    sleep(self.checkTimePeriod)

                sleep(self.electTimePeriod)

        except KeyboardInterrupt:
            print('检测到键盘终止')

    def main(self):
        while True:
            if self.electList:
                print('当前待选课列表: ')
                for index, courseReq in enumerate(self.electList):
                    print(index, '->', courseReq['teachClassCode'],
                          courseReq['courseName'], courseReq['teacherName'])
            if self.withdrawList:
                print('当前待退课列表: ')
                for index, courseReq in enumerate(self.withdrawList):
                    print(index, '->', courseReq['teachClassCode'],
                          courseReq['courseName'], courseReq['teacherName'])

            args = input('>>> ').split()
            if len(args) == 0:
                continue
            op = args[0]

            if op == 'table':
                self.table(args)
            elif op == 'info':
                self.info(args)
            elif op == 'msg':
                self.msg()
            elif op == 'course':
                self.course(args)
            elif op == 'major':
                self.major(args)
            elif op == 'tutor':
                self.tutor()
            elif op == 'book':
                self.book()
            elif op == 'a' or op == 'add' or op == 'wa' or op == 'wadd':
                self.add_list(args)
            elif op == 'd' or op == 'delete' or op == 'wd' or op == 'wdelete':
                self.rmv_list(args)
            elif op == 'e' or op == 'export':
                self.exportList(args)
            elif op == 'i' or op == 'import':
                self.importList(args)
            elif op == 's' or op == 'start':
                self.start()
            elif op == 'q' or op == 'quit':
                self.xuankewang.logout()
                print('Bye')
                break
            elif op == 'l' or op == 'login':
                self.login(args)
            elif op == 'r' or op == 'round':
                self.round(args)
            elif op == 't' or op == 'time':
                inputTime = len(args) > 1 and args[1] or input('输入选课请求间隔: ')
                if inputTime:
                    electTimePeriod = float(inputTime)
                    print('选课间隔设置为', electTimePeriod)
            elif op == 'tt' or op == 'ttime':
                inputTime = len(args) > 1 and args[1] or input('输入轮询请求间隔: ')
                if inputTime:
                    checkTimePeriod = float(inputTime)
                    print('轮询请求间隔设置为', checkTimePeriod)
            elif op == 'f' or op == 'fresh':
                if self.xuankewang.getDataBk():
                    print('课程数据更新成功')
                else:
                    print('课程数据更新失败')
            else:
                self.help(args)


if __name__ == '__main__':
    Spider().main()
