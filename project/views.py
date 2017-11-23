# coding=utf-8

import hashlib
import json
import time
import re
import datetime

from django.shortcuts import render_to_response, redirect, get_object_or_404, RequestContext
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib import auth
from django.contrib.sessions.models import Session
from django.contrib.auth.models import User, Group
from django.db.models import Q
import models
from models import department, project, project_user, public_message, project_delay, project_user_message , project_operator_bussniess_message
from models import user, project_statistics, project_statistics_result, module, project_module
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.utils.translation import ugettext_lazy as _

from project.forms import UserForm, ProjectForm, changedesignForm, delayprojectForm, TestForm, Approveform, LoginForm, \
MessageForm, NoticeForm, ProjectSearchForm ,ConmessageForm, feedbackForm, feedbackCommentForm, addmoduleForm, sdetailForm
from django.views.decorators.cache import cache_page
from django.db.models import Sum

def register(request,uname=''):
    if uname =='':      #若是直接Q系统注册为空,以ldap第一次登录则会传来用户名
        if request.method == "POST":
            uf = UserForm(request.POST)
            if uf.is_valid():
                #返回注册成功页面
                #往Django user表里再插入一条数据
                username = uf.cleaned_data['username']
                password = uf.cleaned_data['password']
                realname = uf.cleaned_data['realname']
                email = username+"@ablesky.com"
                try:
                    user = User.objects.create_user(username=username, email=email, password=password)
                    user.save()
                except:
                    uf = UserForm() 
                    return render_to_response('register.html', {'list':department.objects.filter(~Q(id=100)),
                                                                'error':'注册的用户名已存在'},
                                              context_instance=RequestContext(request))
                uf.save()
  
                #如果是产品部门，加入产品部门权限组
                depid = uf.cleaned_data['departmentid']
                if depid == '3':
                    User.objects.get(username=username).groups.add(3)
    
                #登录
                uid = models.user.objects.filter(username=username)[0].id
                request.session['username'] = username
                request.session['realname'] = realname
                request.session['id'] = uid
    
                #Django 认证系统的登录
                user = auth.authenticate(username=username, password=password)
                auth.login(request, user)
    
                return HttpResponseRedirect("/personal_homepage")
        else:
            uf = UserForm()
        return render_to_response('register.html', {'list':department.objects.filter(~Q(id=100))},
                                  context_instance=RequestContext(request))
    else:
        if request.method == "POST":
            uf = UserForm(request.POST)
            if uf.is_valid():
                #返回注册成功页面
                #往Django user表里再插入一条数据
                username = uf.cleaned_data['username']
                realname = uf.cleaned_data['realname']
                email = username+"@ablesky.com"    
                #如果是产品部门，加入产品部门权限组
                depid = int(uf.cleaned_data['departmentid'])
                if depid == 3:
                    User.objects.get(username=username).groups.add(3)
                uid = models.user.objects.filter(username=username)[0].id
                u = models.user(id=uid, username=username,
                                       realname=realname,                                       
                                       create_time=datetime.datetime.now(),
                                       department=department.objects.get(id=depid),
                                       isactived=1)
                u.save()
                request.session['username'] = username
                request.session['realname'] = realname
                request.session['id'] = uid
    
                #Django 认证系统的登录
                user = auth.authenticate(username=username, password='assecret')
                auth.login(request, user)
    
                return HttpResponseRedirect("/personal_homepage")
        
        userinfo = models.user.objects.filter(username=uname)[0]
        return render_to_response('register.html', {'list':department.objects.filter(~Q(id=100)),
                                                    'info': userinfo})


def logout(request):
    try:
        response = HttpResponseRedirect("/login")
        response.delete_cookie("username")
        response.delete_cookie("password")

        session_key = request.session.session_key
        Session.objects.get(session_key=session_key).delete()
        return response
    except:
        pass
    return HttpResponseRedirect("/login/")

def no_login(request):
    return render_to_response("nologin.html")

def no_perm(request):
    return render_to_response("noperm.html")
def login(request,url):
    agent = request.META.get('HTTP_USER_AGENT','')
    print agent
    template_var = {}
    template_var["url"] = url
    if "username" in request.COOKIES and "password" in request.COOKIES:
        username = request.COOKIES["username"]
        realname = request.COOKIES["realname"]
        password = request.COOKIES["password"]
        _userset = models.user.objects.filter(username__exact=username, password__exact=password)
        if _userset.count() >= 1:
            _user = _userset[0]
            request.session['username'] = username
            request.session['realname'] = realname
        return HttpResponseRedirect(url)
    form = LoginForm()
    if request.method == 'POST':
        form = LoginForm(request.POST.copy())
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = hashlib.md5(form.cleaned_data["password"]).hexdigest()
            isautologin = form.cleaned_data["isautologin"]
            try:                
                user = auth.authenticate(username=username, password=form.cleaned_data["password"]) #先去ldap验证,如果没有再去django的User表里验证,一旦验证成功,返回用户名,不成功,返回None
                if user != None:                   
                    isldap = models.user.objects.filter(username__exact=username)
                    if len(isldap) == 0: #说明该用户通过ldap第一次登录,数据库尚未存储该用户
                        newUser = User.objects.filter(username=username)[0]       #django User表
                        newuser = models.user(username=username, password='1234', realname=newUser.first_name, 
                                              create_time=datetime.datetime.now(), department_id='100', isactived=1) #1234只是为了页面显示好看
                        newuser.save()
                        newUser.password = hashlib.md5('assecret').hexdigest()      #设置django的User表密码为assecret,否则注册后登录无法通过authenticate()验证.看代码的人可以知道ldap登录用户的密码，存在安全风险，不过数据库中看不出来。
                        newUser.save()
                        link = str("/register/" + username)
                        return HttpResponseRedirect(link)
                    elif isldap[0].department_id == 100:
                        link = str("/register/" + username)
                        return HttpResponseRedirect(link)
                    
                    _userset = models.user.objects.filter(username__exact=username)    
                    if _userset.count() >= 1:
                        _user = _userset[0]
                        if _user.isactived:
                            request.session['username'] = _user.username
                            request.session['realname'] = _user.realname
                            request.session['id'] = _user.id
                            auth.login(request, user)
                        else:
                            template_var["error"] = _(u'您输入的帐号未激活，请联系管理员') 
                            template_var["form"] = form
                            return render_to_response("login.html", template_var, context_instance=RequestContext(request))  
                else:
                    template_var["error"] = _(u'您输入的帐号或密码有误，请重新输入')  
                    template_var["form"] = form
                    return render_to_response("login.html", template_var, context_instance=RequestContext(request))                          
            except:
                template_var["error"] = _(u'您输入的帐号或密码有误，请重新输入')
                template_var["form"] = form
                return render_to_response("login.html", template_var, context_instance=RequestContext(request))    
            response = HttpResponseRedirect(url)
            if isautologin:
                response.set_cookie("username", username, 3600)
                response.set_cookie("password", password, 3600)   
            return response
        
    template_var["form"] = form
    return render_to_response("login.html", template_var, context_instance=RequestContext(request))  

def strQ2B(ustring):
    """全角转半角"""
    rstring = ""
    for uchar in ustring:
        inside_code=ord(uchar)
        if inside_code == 12288:                              #全角空格直接转换            
            inside_code = 32 
        elif (inside_code >= 65281 and inside_code <= 65374): #全角字符（除空格）根据关系转化
            inside_code -= 65248

        rstring += unichr(inside_code)
    return rstring

def new_project(request, pid='', nid=''):
    #没登陆的提示去登录
    if not request.user.is_authenticated():
        return HttpResponseRedirect("/nologin")

    editdate = 1
    #编辑的得有编辑权限
    if pid:
        uid = request.session['id']
        cpro = models.project.objects.get(id=pid)
        
        #flag标志
        # flag = 0
        mid = [cpro.leader_p_id, cpro.designer_p_id, cpro.tester_p_id, cpro.business_man_id, cpro.operator_p_id, cpro.customer_service_id]
        #如果是负责人且有编辑权限才可以进入编辑页面
        if (uid in mid or request.user.has_perm('auth.change_permission')) and request.user.has_perm('project.change_project'):
        #是负责人或者是项目经理
            if not request.user.has_perm('auth.change_permission'):
            #编辑计划上线时间的标记
                editdate = 0
        else:
            return HttpResponseRedirect("/noperm")
    else:
        #新建的得有新建权限
        if not pid and not request.user.has_perm('project.add_project'):
            return HttpResponseRedirect("/noperm") 
    
    form = ProjectForm()
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            type_p = form.cleaned_data['type_p']
            priority = form.cleaned_data['priority']
            pname = form.cleaned_data['pname']
            description = form.cleaned_data['description']
            #新增以下四项支持项目打分
            pplan_score = form.cleaned_data['p_plan_score']
#            print pplan_score, description
            pps_dpt = form.cleaned_data['plan_score_description']
            pactual_score = form.cleaned_data['p_actual_score']
            pas_dpt = form.cleaned_data['actual_score_description']
            status = form.cleaned_data['status']
            leaderid = form.cleaned_data['leader']
            leader = models.user.objects.get(id=leaderid)
            designer = form.cleaned_data['designer']
            tester = form.cleaned_data['tester']
            business_man = form.cleaned_data['business_man']
            operator_p = form.cleaned_data['operator_p']
            customer_service = form.cleaned_data['customer_service']
            role = [designer, tester, business_man, operator_p, customer_service]
            roles = []
            for item in role:
                if item:
                    roles.append(models.user.objects.get(id=item))
                else:
                    roles.append(item)
            sdate = form.cleaned_data['startdate']
            pdate = form.cleaned_data['plandate']
            psdate = form.cleaned_data['psdate']
            pedate = form.cleaned_data['pedate']
            dsdate = form.cleaned_data['dsdate']
            dedate = form.cleaned_data['dedate']
            tsdate = form.cleaned_data['tsdate']
            tedate = form.cleaned_data['tedate']
            ppath = form.cleaned_data['ppath']
            dppath = form.cleaned_data['dppath']
            tppath = form.cleaned_data['tppath']
            tcpath = form.cleaned_data['tcpath']
            trpath = form.cleaned_data['trpath']
            relateduser0 = form.cleaned_data['relateduser0']
            relateduser1 = form.cleaned_data['relateduser1']
            relateduser2 = form.cleaned_data['relateduser2']
            relateduser3 = form.cleaned_data['relateduser3']
            relateduser4 = form.cleaned_data['relateduser4']
            relateduser5 = form.cleaned_data['relateduser5']
            countsql = form.cleaned_data['countsql']
            countsql = strQ2B(countsql)
            sqlremoved = form.cleaned_data['sqlremoved']
            remark_p = form.cleaned_data['remark_p']

            if pid == '' or nid == '1':
                pro = models.project(type_p=type_p, priority=priority, \
                    project=pname, description=description, \
                    status_p=status, leader_p=leader, \
                    designer_p=roles[0], tester_p=roles[1], start_date=sdate, \
                    business_man =roles[2], operator_p = roles[3],\
                    customer_service = roles[4],\
                    expect_launch_date=pdate, \
                    estimated_product_start_date=psdate, \
                    estimated_product_end_date=pedate, \
                    estimated_develop_start_date=dsdate, \
                    estimated_develop_end_date=dedate, \
                    estimated_test_start_date=tsdate, \
                    estimated_test_end_date=tedate, blueprint_p=ppath, \
                    develop_plan_p=dppath, test_plan_p=tppath, \
                    test_case_p=tcpath, test_report_p=trpath, \
                    remark_p =remark_p, isactived=1)
            else:
                rdate = models.project.objects.get(id=pid).real_launch_date
                pnum = models.project.objects.get(id=pid).praise_p
                pro = models.project(id=pid, type_p=type_p, \
                    priority=priority,project=pname, \
                    description=description, \
                    status_p=status, leader_p=leader, \
                    designer_p=roles[0], tester_p=roles[1], \
                    business_man = roles[2], \
                    operator_p = roles[3],\
                    customer_service = roles[4],\
                    start_date=sdate, \
                    expect_launch_date=pdate, \
                    real_launch_date=rdate, \
                    estimated_product_start_date=psdate, \
                    estimated_product_end_date=pedate, \
                    estimated_develop_start_date=dsdate, \
                    estimated_develop_end_date=dedate, \
                    estimated_test_start_date=tsdate, \
                    estimated_test_end_date=tedate, blueprint_p=ppath, \
                    develop_plan_p=dppath, test_plan_p=tppath, \
                    test_case_p=tcpath, test_report_p=trpath, \
                    remark_p=remark_p,isactived=1, praise_p=pnum)
            pro.save()
            #存完项目，存相关产品测试开发等人员信息
            
            #如果是新建就取出刚才存在的项目id,否则是编辑则删掉此前的用户与项目的关系
            if pid == '' or nid =='1':
                pid = models.project.objects.filter\
                (project=pname).order_by("-id")[0].id
                
                if request.POST['countsql']:
                    m = project_module(project_id=pid, module_id=100, isactived=1)  #新建项目若有sql的情况下默认归入综合类模块
                    m.save()
                
            else:
                models.project_user.objects.filter(project_id=pid).delete()

                if request.POST['countsql']:
                    try:
                        project_module.objects.get(project_id=pid)
                    except:
                        m = project_module(project_id=pid, module_id=100, isactived=1)      #编辑项目时,若sql有值,看是否有所属模块,没有就存
                        m.save()
                else:
                    try:
                        project_module.objects.get(project_id=pid)
                        project_module.objects.get(project_id=pid).delete()     #编辑项目时,若无sql,看是否有所属模块,有就删除
                    except:
                        pass

                if sqlremoved:
                    sqlid = sqlremoved.split(',');
                    for sid in sqlid:
                        if len(sid):
                            asql = models.project_statistics.objects.get(id=int(sid))
                            asql.isactived = 0
                            asql.save()
            
            relateduser = [relateduser0, relateduser1, relateduser2, relateduser3, relateduser4, relateduser5]
            all_p_user = []
            for i in range(len(relateduser)):
                #把相关人员的id存入列表中
                relateduser[i] = relateduser[i].replace(" ", "").split(",")
                if len(relateduser[i]):          
                    #存用户与项目的关系
                    for uid in relateduser[i]:
                        if uid: 
                            #先把要存的人都放入列表all_p_user中
                            project_user = models.project_user\
                            (username_id=uid, project_id=pid, roles=i, isactived=1)
                            all_p_user.append(project_user)

            #最后再一起插入数据库
            models.project_user.objects.bulk_create(all_p_user)

            #存完人员,存统计查询语句
            psql = countsql.split(";")
#            print psql
            for sql in psql:
                if ":" in sql:
                    sqlstr = sql.split(":")
                    #如果分隔不是4证明填写不规范不保存
                    if len(sqlstr) != 5 :
                        continue
                    sqlid = sqlstr[0]
                    item = sqlstr[1]
                    db = sqlstr[2]
                    sql = sqlstr[3]
                    isgraph = int(sqlstr[4]) 
                    if sqlid:
                        project_statistics = models.project_statistics.objects.get(id=sqlid)                        
                        project_statistics.is_graph = isgraph             #只更新可能变动的列就可以了.
                        if project_statistics.is_editable == 0:
                            project_statistics.save()
                            continue
                        project_statistics.item = item 
                        project_statistics.db = db
                        project_statistics.sql = sql                   #不能编辑的sql就不能保存更改了
                        
                    else:
                        project_statistics = models.project_statistics(
                                        project_id=pid, item=item, db=db, sql=sql, is_graph=isgraph, is_editable=1)
                    project_statistics.save()
            #存项目分数,如果已存过，则先删除旧的，再存新的，实现编辑功能，一条pid对应一条scroe记录;
            #要判断只有项目经理才可以存项目分数
            if request.user.has_perm('project.add_project'):
                try:
                    models.pro_score.objects.filter(project_id=pid).delete()
                finally:
                    pro_score = models.pro_score(project_id=pid, p_plan_score=pplan_score, p_plan_dpt=pps_dpt,
                                                 p_actual_score=pactual_score, p_actual_dpt=pas_dpt)
                    pro_score.save()

            #将各负责人加入到相应负责人权限组
            allmasters = [[leaderid, 4], [designer, 5], [tester, 6], [business_man, 7], [operator_p, 8], [customer_service, 9]]
            for m in allmasters:
                if m[0]:
                    mname = models.user.objects.get(id=m[0]).username
                    User.objects.get(username=mname).groups.add(m[1])
      
            #发消息
            sendmessage(request,status,pid)                           
            return redirect('/projectlist/')
        else:
            dateloop = ['psdate', 'pedate', 'dsdate', 'dedate', 'tsdate', 'tedate', 'startdate', 'plandate']
            prodate = []
            for item in dateloop:
                cdate = request.POST[item]
                if cdate:
                    idate = datetime.datetime.strptime(cdate, "%Y-%m-%d")
                else:
                    idate = None
                prodate.append(idate)
            if request.POST['leader']:
                luser = models.user.objects.get(id=request.POST['leader'])
            else:
                luser = None
            relateduser0 = request.POST['relateduser0']
            relateduser1 = request.POST['relateduser1']
            relateduser2 = request.POST['relateduser2']
            relateduser3 = request.POST['relateduser3']
            relateduser4 = request.POST['relateduser4']
            relateduser5 = request.POST['relateduser5']
            
            relateduser = [relateduser0, relateduser1, relateduser2, relateduser3, relateduser4, relateduser5]
            people = []
            allpeople = []
            for i in range(len(relateduser)):
                relateduser[i] = relateduser[i].replace(" ", "").split(",")         
                for uid in relateduser[i]:
                    if uid:
                        tuser = models.user.objects.get(id=int(uid))
                        people.append(tuser)
                allpeople.append(people)
                people = []

            related_user = {'pd':allpeople[0], 'dev': allpeople[1], 'qa': allpeople[2], \
            'bm': allpeople[3], 'cs': allpeople[4], 'op': allpeople[5]}
            dpid = request.POST['designer']
            tpid = request.POST['tester']
            if dpid:
                dpid = int(dpid)
            if tpid:
                tpid = int(tpid)

            pro = {'type_p':request.POST['type_p'],
                   'priority':request.POST['priority'],
                   'project':request.POST['pname'],
                   'description':request.POST['description'],
                   'status_p':request.POST['status'],
                   'leader_p_id':request.POST['leader'],
                   'designer_p_id':dpid,
                   'tester_p_id':tpid,
                   'start_date':prodate[6],
                   'expect_launch_date':prodate[7],
                   'estimated_product_start_date':prodate[0],
                   'estimated_product_end_date':prodate[1],
                   'estimated_develop_start_date':prodate[2],
                   'estimated_develop_end_date':prodate[3],
                   'estimated_test_start_date':prodate[4],
                   'estimated_test_end_date':prodate[5],
                   'blueprint_p':request.POST['ppath'],
                   'develop_plan_p':request.POST['dppath'],
                   'test_plan_p':request.POST['tppath'],
                   'test_case_p':request.POST['tcpath'],
                   'test_report_p':request.POST['trpath'],
                   'remark_p':request.POST['remark_p'],}

            dt_temp = {}
            dt = {}
            #处理时间为空,无法计算时间差
            if (pro['estimated_product_end_date'] != None) & (pro['estimated_product_start_date'] != None):
                dt_temp['p'] = pro['estimated_product_end_date'] - pro['estimated_product_start_date']
                dt['ptime'] = int(dt_temp['p'].days+1)
            else:
                dt['ptime'] = 0
            if (pro['estimated_develop_end_date'] != None) & (pro['estimated_develop_start_date'] != None):
                dt_temp['d'] = pro['estimated_develop_end_date'] - pro['estimated_develop_start_date']
                dt['dtime'] = int(dt_temp['d'].days+1)
            else:
                dt['dtime'] = 0
            if (pro['estimated_test_end_date'] != None) & (pro['estimated_test_start_date'] != None):
                dt_temp['t'] = pro['estimated_test_end_date'] - pro['estimated_test_start_date']
                dt['ttime'] = int(dt_temp['t'].days+1)
            else:
                dt['ttime'] = 0

            res = {'pro':pro, 'user':luser, 'reuser':related_user, 'dt': dt, 'sql':request.POST['countsql']}
            return render_to_response('newproject.html', \
                {'res':res, 'form':form,'editdate':editdate}, context_instance=RequestContext(request))

    return render_to_response('newproject.html', \
        {'form':form, 'editdate':editdate}, context_instance=RequestContext(request))


#发消息
def sendmessage(request,status,pid):
    # 项目设计完成需要给业务负责人和产品负责人发消息，project_operator_bussniess_message和public_message
    # project_user_message这三个表
    # 设计完成isactived存2，测试中isactived存3，上线给留言发消息isactived存1，上线发公告isactived存0 
    # --杜
    if status == u"设计完成":
        flag = 0
        prolist = public_message.objects.filter\
        (project=pid).filter(isactived=2).order_by("-id")
        try:
            prolist[0].isactived
        except IndexError:
            try:
                request.session['id']
            except KeyError:
                return HttpResponseRedirect("/nologin")
            else:
                flag = 1                        
        else:
            if prolist[0].isactived != 2:
                try:
                    request.session['id']
                except KeyError:
                    return HttpResponseRedirect("/nologin")
                else:
                    flag = 1
        if flag == 1:        
            usrid = request.session['id']
            project = models.project.objects.get(id=pid)
            time = datetime.datetime.now().strftime("%Y-%m-%d %H:%I:%S")
            content = project.project + u"于" + time + u"设计完成，请立即查看设计图并确认！"    
            uids = []
            if project.business_man_id > 0 :
                uids.append(project.business_man_id)
            if project.operator_p_id > 0 :
                uids.append(project.operator_p_id)
            if project.customer_service_id > 0 :
                uids.append(project.customer_service_id)
            uids = set(uids)
            for uid in uids :
                # 存表public_message
                pmessage = public_message(project=pid, \
                                          publisher=uid, content=content, type_p="message", \
                                          publication_date=datetime.datetime.now(), \
                                          delay_status="未确认" , \
                                          isactived=2)
                pmessage.save()
                # 存表project_user_message
                # 存该项目的业务负责人、客服负责人和运营负责人，只有这三个个人哦 
                messageid = public_message.objects.filter(publisher=uid).order_by("-id")[0]
                ppmessage = project_user_message(userid_id=uid , messageid_id=messageid.id , \
                                                 project_id=pid , isactived=True)
                ppmessage.save()
            # 存表project_operator_bussniess_message
            # 存该项目的业务负责人、客服负责人和运营负责人，只有这三个个人哦
            if project.business_man_id > 0 :
                pmessage = project_operator_bussniess_message(userid_id=project.business_man_id , project_id=pid , \
                                                              user_type="业务" , \
                                                              title="设计完成，请立即查看设计图并确认！" , \
                                                              status="未确认设计" , publication_date=datetime.datetime.now(), \
                                                              isactived=False)
                pmessage.save()
            if project.operator_p_id > 0 :
                pmessage = project_operator_bussniess_message(userid_id=project.operator_p_id , project_id=pid , \
                                                              user_type="运营" , \
                                                              title="设计完成，请立即查看设计图并确认！" , \
                                                              status="未确认设计" , publication_date=datetime.datetime.now(), \
                                                              isactived=False)
                pmessage.save()
            if project.customer_service_id > 0 :
                pmessage = project_operator_bussniess_message(userid_id=project.customer_service_id , project_id=pid , \
                                                              user_type="客服" , \
                                                              title="设计完成，请立即查看设计图并确认！" , \
                                                              status="未确认设计" , publication_date=datetime.datetime.now(), \
                                                              isactived=False)
                pmessage.save() 
                                                




    if status == u"测试中":
        flag = 0
        prolist = public_message.objects.filter\
        (project=pid).filter(isactived=3).order_by("-id")
        try:
            prolist[0].isactived
        except IndexError:
            try:
                request.session['id']
            except KeyError:
                return HttpResponseRedirect("/nologin")
            else:
                flag = 1                        
        else:
            if prolist[0].isactived != 3:
                try:
                    request.session['id']
                except KeyError:
                    return HttpResponseRedirect("/nologin")
                else:
                    flag = 1
        if flag == 1:        
            usrid = request.session['id']
            project = models.project.objects.get(id=pid)
            time = datetime.datetime.now().strftime("%Y-%m-%d %H:%I:%S")
            content = project.project + u"于" + time + u"已发测试版，请在上线前联系项目负责人并确认验收！"    
            uids = []
            if project.business_man_id > 0 :
                uids.append(project.business_man_id)
            if project.operator_p_id > 0 :
                uids.append(project.operator_p_id)
            if project.customer_service_id > 0 :
                uids.append(project.customer_service_id)
            uids = set(uids)
            for uid in uids :
                # 存表public_message
                pmessage = public_message(project=pid, \
                                          publisher=uid, content=content, type_p="message", \
                                          publication_date=datetime.datetime.now(), \
                                          delay_status="未确认" , \
                                          isactived=3)
                pmessage.save()
                # 存表project_user_message
                # 存该项目的业务负责人、客服负责人和运营负责人，只有这三个个人哦 
                messageid = public_message.objects.filter(publisher=uid).order_by("-id")[0]
                ppmessage = project_user_message(userid_id=uid , messageid_id=messageid.id , \
                                                 project_id=pid , isactived=True)
                ppmessage.save()
            # 存表project_operator_bussniess_message
            # 存该项目的业务负责人、客服负责人和运营负责人，只有这三个个人哦
            if project.business_man_id > 0 :
                pmessage = project_operator_bussniess_message(userid_id=project.business_man_id , project_id=pid , \
                                                              user_type="业务" , \
                                                              title="已发测试版，请在上线前联系项目负责人并确认验收！" , \
                                                              status="项目未验收" , publication_date=datetime.datetime.now(), \
                                                              isactived=False)
                pmessage.save()
            if project.operator_p_id > 0 :
                pmessage = project_operator_bussniess_message(userid_id=project.operator_p_id , project_id=pid , \
                                                              user_type="运营" , \
                                                              title="已发测试版，请在上线前联系项目负责人并确认验收！" , \
                                                              status="项目未验收" , publication_date=datetime.datetime.now(), \
                                                              isactived=False)
                pmessage.save()
            if project.customer_service_id > 0 :
                pmessage = project_operator_bussniess_message(userid_id=project.customer_service_id , project_id=pid , \
                                                              user_type="客服" , \
                                                              title="已发测试版，请在上线前联系项目负责人并确认验收！" , \
                                                              status="项目未验收" , publication_date=datetime.datetime.now(), \
                                                              isactived=False)
                pmessage.save()
                
    #上线后插条公告,如果表中项目ID存在,排序看isactived是否为0,如果不存在该项目ID或最小的isactived=0,则插入公告
    if status == u"已上线":
        flag = 0
        prolist = public_message.objects.filter\
        (project=pid).order_by("isactived")
        try:
            prolist[0].isactived
        except IndexError:
            try:
                request.session['id']
            except KeyError:
                return HttpResponseRedirect("/nologin")
            else:
                flag = 1                        
        else:
            if prolist[0].isactived != 0:
                try:
                    request.session['id']
                except KeyError:
                    return HttpResponseRedirect("/nologin")
                else:
                    flag = 1
        if flag == 1:        
            usrid = request.session['id']
            project = models.project.objects.get(id=pid)
            time = datetime.datetime.now().strftime("%Y-%m-%d %H:%I:%S")
            content = project.project + u"于"+time+u"已上线"
            pmessage = public_message(project=pid, \
                                      publisher=usrid, content=content, type_p="notice", \
                                      publication_date=datetime.datetime.now(), \
                                      isactived=False)
            pmessage.save()
                    
            #先判断在项目上线之前有没有留言的人
            try:
                related_user = models.project_feedback.objects.filter(project_id=pid)
            except KeyError:
                None
            else:
                #项目上线，给留言者发的消息存在消息表中
                string = project.project + u"已上线，您可以去体验并跟踪反馈机构的体验效果啦"
                pub_message = public_message(project=pid, publisher=usrid, content=string, \
                                             type_p="message", publication_date=datetime.datetime.now(), delay_status="已上线", isactived=1)
                pub_message.save()
                #先判断在项目上线之前有没有留言的人
                #从留言表中把此项目相关的留言数据读取出来（留言者id）
                message = public_message.objects.filter(project=pid).order_by("-id")[0]
                #给项目和消息创建关系
                pro_u_messages = []
                users = []
                for i in related_user:
                    users.append(i.feedback_member_id)
                    #判断是否有回复反馈人的人feedbackid_id是反馈表中id
                    try:
                        back_c_user = models.project_feedback_comment.objects.filter(feedbackid_id=i.id)
                    except KeyError:
                        None
                    else:
                        for j in back_c_user:
                            users.append(j.feedback_member_c_id)  
                users = set(users)
                for u in users:
                    uid = u
                    megid = message.id
                    pro_u_message = project_user_message(userid_id=uid, messageid_id=megid, project_id=pid, isactived='1')
                    pro_u_messages.append(pro_u_message)
                models.project_user_message.objects.bulk_create(pro_u_messages)  
            ### 
                    
            project.real_launch_date = datetime.datetime.now()
            project.save() 

def isNone(s):
    if s is None or (isinstance(s, basestring) and len(s.strip()) == 0):
        return True
    else:
        return False         
    
def project_list(request):
    createtag = logintag = changetag =delaytag = deletetag = edittag = user_id = auth_changetag = 0    
    #没登陆的提示去登录
    if not request.user.is_authenticated():
        return HttpResponseRedirect("/login")
    else:
        logintag = 1
        user_id = request.session['id']
    #判断是否登录，给一个是否登录的标记值,logintag=1为已登录
    #以下是权限标记，createtag是发布相似的权限
    if logintag == 1:
        if request.user.has_perm("project.change_public_message"):
            changetag = 1
        if request.user.has_perm('project.change_project'):
            edittag = 1
        if request.user.has_perm("project.add_project_delay"):
            delaytag = 1
        if request.user.has_perm("project.delete_project"):
            deletetag = 1
        if request.user.has_perm("auth.change_permission"):
            auth_changetag = 1
        if  request.user.has_perm('project.add_project'):
            createtag = 1
    #notice
    noticess = public_message.objects.filter(type_p='notice').order_by('-id')
    count = noticess.count()
    notices = noticess[:5]      
    ##
    projectlist = None
    print request.GET.get("project")
    project_id = "" if isNone(request.GET.get("id"))else request.GET.get("id")
    project_name = "" if isNone(request.GET.get("project"))else request.GET.get("project")
    start_date_s = "" if isNone(request.GET.get("start_date_s")) else request.GET.get("start_date_s")
    end_date_s = "" if isNone(request.GET.get("end_date_s")) else request.GET.get("end_date_s")
    status_p = "" if isNone(request.GET.get("status_p")) else request.GET.get("status_p")
    leader_p = "" if isNone(request.GET.get("leader_p")) else request.GET.get("leader_p")
    type_p = "" if isNone(request.GET.get("type_p")) else request.GET.get("type_p")

    #将get到的日期参数由string类型（实际type的时候显示是unicode，暂时未知）转换成datetime类型。
    #strptime是将str类型转换为struct_time,然后再用datetime.date将time类型转换为datetime类型
    #"*"表示将列表中的数据作为函数的参数，如果是**则是将字典中的数据作为函数的参数
    if not isNone(start_date_s):
        start_time = time.strptime(start_date_s ,"%Y-%m-%d")
        start_date_s = datetime.date(*start_time[:3])
    if not isNone(end_date_s):
        end_time = time.strptime(end_date_s ,"%Y-%m-%d")
        end_date_s = datetime.date(*end_time[:3])

    project_user_list = None
    #projectlist = project.objects.all()
    if request.method == 'POST':
        search_form = ProjectSearchForm(request.POST)
        if search_form.is_valid():
            project_id = search_form.cleaned_data['id']
            project_name = search_form.cleaned_data['project']
            start_date_s = search_form.cleaned_data['start_date_s']
            #print(start_date_s)
            end_date_s = search_form.cleaned_data['end_date_s']
            status_p = search_form.cleaned_data['status_p']
            leader_p = search_form.cleaned_data['leader_p']
            type_p = search_form.cleaned_data['type_p']
            #先按状态排序，状态相同按priority排
            projectlist = models.project.objects.filter().order_by("-status_p","-priority")
    else:
        projectlist = models.project.objects.all().order_by("-status_p","-priority")
                                           
    if not isNone(project_id):
        project_id=project_id.strip()
        if(project_id.isdigit()):
            projectlist = projectlist.filter(id=project_id)
        else:
            projectlist = projectlist.filter(id=0)
    if not isNone(project_name):
        projectlist = projectlist.filter(project__contains=project_name.strip())
    if not isNone(start_date_s):
        projectlist = projectlist.filter(start_date__gte=start_date_s)
    if not isNone(end_date_s):
        projectlist = projectlist.filter(start_date__lte=end_date_s)
    if not isNone(status_p):
        projectlist = projectlist.filter(status_p=status_p.strip())
    #新增的筛选项，类型
    if not isNone(type_p):
        projectlist = projectlist.filter(type_p=type_p.strip())
    if not isNone(leader_p):
        #projectlist = projectlist.filter(leader_p__username__contains=leader_p.strip())
        project_user_list = models.project_user.objects.filter(username__realname__contains=leader_p.strip())
        projectids = []
        for p in project_user_list:
            projectids.append(p.project.id)
        projectlist = projectlist.filter(pk__in=projectids)

    """分页"""
    paginator = Paginator(projectlist, 25)
    page = request.GET.get('page')
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1
    try:
        projectobj = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        projectobj = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        projectobj = paginator.page(paginator.num_pages)
    #判断项目是否显示橙色和选中相应项目负责人
    rendering = {}
    proid = []
    for org in projectobj:
        proid.append(org.id)
        l = []
        stu_col = u_name = ''
        business_man = design = prom = tester = operator = customer_service = ''
        list_user =  models.project_user.objects.select_related().filter(project = org.id)
        # u_name = list_user.distinct().values_list("username",flat=True)#查询出id下的所有成员，显示的是列表，通过外键取不出姓名
        for u in list_user:
            pattern = re.compile(u.username.realname)
            match = pattern.search(u_name)
            if not match:
                u_name = u_name + ' ' + u.username.realname
        l.append(u_name)   
        if org.status_p !=u'已暂停' and org.status_p != u'已上线' :
            curtime = datetime.datetime.now()
            nowtime = curtime.strftime("%Y-%m-%d ") 
            expect_date = org.expect_launch_date
            if org.expect_launch_date and org.status_p != u'运营推广' and expect_date.strftime("%Y-%m-%d ") < nowtime:
                stu_col = "style=background-color:#ff9933"
            l.append(stu_col)
        if org.type_p == u'产品' and org.status_p == u'需求讨论中' or org.status_p == u'设计中' or org.status_p == u'设计完成':
            design =  "style=color:#339966;font-weight:bold"    
        else:
            if org.status_p == u'需求讨论中':
                business_man =  "style=color:#339966;font-weight:bold"
            if org.status_p == u'设计中' or org.status_p == u'设计完成':
                design =  "style=color:#339966;font-weight:bold"
        if org.status_p == u'开发中':
            prom = "style=color:#339966;font-weight:bold"
        if org.status_p == u'测试中':
            tester = "style=color:#339966;font-weight:bold"
        if org.status_p == u'运营推广':
            operator = "style=color:#339966;font-weight:bold"
        l.append(business_man)
        l.append(design)
        l.append(prom)
        l.append(tester)
        l.append(operator)
        l.append(customer_service)
        rendering[org.id]= l 
    # 项目使用量统计
    filter_project =[]  
    cpcount = []    
    pcount = models.project_statistics.objects.filter(project_id__in = proid)
    # p1 = models.project_statistics.objects.distinct().values_list('project_id',flat=True)
    # pcount = list(set(p1).intersection(set(proid))) 
    for c in pcount: 
        if c.project_id not in cpcount: #project_id 去重
            filter_project.append(pcount.filter(project_id=c.project_id).order_by("total")[0]) #每个项目只返回一组统计值最大的记录,方便页面显示
            cpcount.append(c.project_id)   
    return render_to_response('projectlist.html', RequestContext(request, {'projectobj':projectobj, \
            'rendering':rendering, 'pcount':pcount, 'fproject':filter_project,  'project_id':project_id, \
            'project_name':project_name, 'start_date_s':start_date_s, 'end_date_s':end_date_s, \
            "status_p":status_p, "leader_p":leader_p,"type_p":type_p, 'notices':notices, \
            'count':count, "logintag":logintag, "changetag":changetag, "delaytag":delaytag, "deletetag":deletetag,\
            "edittag":edittag, "user_id":user_id, "auth_changetag":auth_changetag, "createtag":createtag}))
    
def praise(request ,pid):
    if request.META.has_key('HTTP_X_FORWARDED_FOR'):
        ip = request.META['HTTP_X_FORWARDED_FOR']
    else:
        ip = request.META['REMOTE_ADDR']
    p = models.project.objects.get(id=int(pid))
    praisecount = p.praise_p+1
    p.praise_p = praisecount
    p.save()


    return HttpResponse(praisecount)
#@cache_page(60)    
def detail(request, pid='', nid=''):
    """
    pid是项目id
    nid为1时,表示发布与项目pid相似的项目
    """
    try:         #没登录的去登录页面
        request.session['id']
    except:
        return HttpResponseRedirect('/login')
    pro = models.project.objects.get(id=int(pid))
    user = models.user.objects.get(id=pro.leader_p_id)
    devs = models.user.objects.filter(Q(project_user__project_id=pid), Q(project_user__roles=1), Q(department_id=2) | Q(department_id=4) | Q(department_id=5) | Q(department_id=13))
    bms = models.user.objects.filter(Q(project_user__project_id=pid), Q(project_user__roles=3), Q(department_id=12) | Q(department_id=9) | Q(department_id=7)| Q(department_id=6))
    ops = models.user.objects.filter(Q(project_user__project_id=pid), Q(project_user__roles=4), Q(department_id=3) | Q(department_id=8) | Q(department_id=12)| Q(department_id=9) | Q(department_id=7) | Q(department_id=6))
    #这个列表用来存测试产品销售客服
    p_role = []
    #这个列表用来存测试产品销售客服的部门id和roles值
    dep_id = [[1,2], [3,0], [7,5]]
    for item_id in dep_id:
        p_role.append(models.user.objects.filter(project_user__project_id=pid, department_id=item_id[0], project_user__roles=item_id[1]))

    related_user = {'qa':p_role[0], 'dev': devs, 'pd': p_role[1], 'bm': bms, 'cs': p_role[2], 'op': ops}
   

    dt_temp = {}
    dt = {}
    #处理时间为空,无法计算时间差
    if (pro.estimated_product_end_date != None) & (pro.estimated_product_start_date != None):
        dt_temp['p'] = pro.estimated_product_end_date - pro.estimated_product_start_date
        dt['ptime'] = int(dt_temp['p'].days+1)
    else:
        dt['ptime'] = 0
    if (pro.estimated_develop_end_date != None) & (pro.estimated_develop_start_date != None):
        dt_temp['d'] = pro.estimated_develop_end_date - pro.estimated_develop_start_date
        dt['dtime'] = int(dt_temp['d'].days+1)
    else:
        dt['dtime'] = 0
    if (pro.estimated_test_end_date != None) & (pro.estimated_test_start_date != None):
        dt_temp['t'] = pro.estimated_test_end_date - pro.estimated_test_start_date
        dt['ttime'] = int(dt_temp['t'].days+1)
    else:
        dt['ttime'] = 0
    editboolean = False
    if nid == '1':
        pro_sql = ""
    else:
        pro_sql = models.project_statistics.objects.filter(project_id=pid, isactived=1)
    # sql = ''
    # for p in pro_sql:
    #     sql = sql + p.item + ':' + p.db + ':' + p.sql + ';' 
    if len(pro_sql)==0:
        sql_status = '未填写'
    else:
        sql_status = '已填写'
#各部门负责人确认状态  
    confirmation = {}
    bm_status = models.project_operator_bussniess_message.objects.filter(project_id=pid, user_type='业务')
    op_status = models.project_operator_bussniess_message.objects.filter(project_id=pid, user_type='运营')
    cs_status = models.project_operator_bussniess_message.objects.filter(project_id=pid, user_type='客服')
    conf_status = [bm_status, op_status, cs_status]
    name = ['bm', 'op', 'cs']
    b = 0 #用来控制名字
    for sec in conf_status:
        a = 0
        design_col = 'red' 
        check_col = 'red'
        if sec:
            check = ''
            for item in sec:            
                if item.confirm_design_date:
                    design_col = '#339966'
                    design_date = item.confirm_design_date
                    design = design_date.strftime("%Y-%m-%d ") + item.status
                else:
                    if item.check_date:
                        check_col ='#339966'
                        check_date = item.check_date
                        check = check_date.strftime("%Y-%m-%d ") + item.status
                        design = ''
                    else:                    
                        if a == 0:
                            design = item.status
                        else:
                            check = item.status
                a = a + 1
        else:
            design_col = design = check_col = check = ''
        confirmation[name[b]] = []                                      #用来存储不同部门的四个值：０是设计确认颜色值，１是设计确认状态文字，２是测试版确认状态的颜色值，３是测试版确认状态的文字。
        confirmation[name[b]].append(design_col)
        confirmation[name[b]].append(design)
        confirmation[name[b]].append(check_col)
        confirmation[name[b]].append(check)
        b = b + 1       
    
    current_uid = request.session['id'] #把当前登录用户的id传给页面，方便记录反馈人ID
    pro_feedback = models.project_feedback.objects.filter(project_id=pid).order_by("-feedback_date")
    fc = {}
    for item in pro_feedback:
        feedback_comment = models.project_feedback_comment.objects.filter(feedbackid_id=item.id).order_by("-feedback_date_c")
        fc[item] = feedback_comment
    
#    print sorted(fc.iteritems(), key=lambda d:d[0].id, reverse = True)  如果想按评论也倒序显示，可以使用这句先将字典变成列表
    
    #取项目分数信息
    ps_info = {'pps':'', 'pps_dpt':'', 'pas':'', 'pas_dpt':''}
    try:
        ps_obj = models.pro_score.objects.get(project_id=pid)
        ps_info['pps'] = ps_obj.p_plan_score
        ps_info['pps_dpt'] = ps_obj.p_plan_dpt
        ps_info['pas'] = ps_obj.p_actual_score
        ps_info['pas_dpt'] = ps_obj.p_actual_dpt
    except:
#        ps_info['pps'] = ps_info['pps_dpt'] = ps_info['pas'] = ps_info['pas_dpt'] = ''
        pass
    print ps_info     
    try:
        request.user 
        auth_id = [pro.leader_p_id, pro.designer_p_id, pro.tester_p_id, 
                   pro.business_man_id, pro.operator_p_id, pro.customer_service_id]            
        if(request.user.has_perm('auth.change_permission') or request.session['id'] in auth_id):
            editboolean = True
        
    finally:
        if '/detail/' in request.path:
            # 详情页项目经理可以看到已报名项目的人
            # 如果不是项目经理就判断是否已报名
            # signed_PM: 1 已报   0 未报
            signed_info = {}            
            for section,users in related_user.items():
                for us in users:
                    if us.realname==u"招募PM":
                        pm_info = signed_pro(pid, "PM", editboolean, current_uid)
                        signed_info['pm_info'] = [1, pm_info]
                    if us.realname in [u"招募后端", u"招募前端", u"招募App", u"招募flash", u"招募C++"]:   
                        dev_info = signed_pro(pid, "dev", editboolean, current_uid)
                        signed_info['dev_info'] = [1, dev_info]
                    if us.realname in [u"招募web测试", u"招募client测试"]:
                        test_info = signed_pro(pid, "test", editboolean, current_uid)
                        signed_info['test_info'] = [1, test_info]
                    if us.realname in [u"招募产品", u"招募UI"]:
                        pd_info = signed_pro(pid, "PD", editboolean, current_uid)
                        signed_info['pd_info'] = [1, pd_info]
            # test把项目描述由字符串拆成列表
            pro.description = pro.description.split('\n')
            res = {'pro':pro, 'user':user, 'dt': dt, 'reuser': related_user, 'editbool': editboolean, 
                   'sql': sql_status, 'confirmation': confirmation, 'curuid': current_uid, 
                   'feedback': [len(pro_feedback), fc], 'signed_info': signed_info, 'ps': ps_info}
            return render_to_response('detail.html', {'res': res})
        elif '/editproject' in request.path:
            edittag = 1
            editdate = 1
            isdevs = 1
            isope = 0
            if nid == '1':
                #此时是在发布相似项目
                edittag = 0
            else:
                #在编辑项目
                user_id = request.session['id']
                dep_id = models.user.objects.filter(id=user_id)[0].department_id

                #isdevs标记当前登陆者是不是技术人员      
                if dep_id not in [1,2,3,4,5,13]:
                    isdevs = 0
                    bs_id = models.project.objects.get(id=pid).operator_p_id
                    if user_id == bs_id:
                        isope = 1

                if not request.user.has_perm('auth.change_permission'):
                    editdate = 0
            print ps_info['pps']
#            print pro.description
            res = {'pro':pro, 'user':user, 'dt': dt, 'reuser': related_user, 
                   'request': edittag, 'editid':nid, 'sql': pro_sql, 'ps': ps_info}
            # editdate用来判断是否PMO
            return render_to_response('newproject.html', {'res': res, 'editdate':editdate, 'isdevs':isdevs, 'isope':isope})

def signed_pro(pid, type, editboolean, current_uid):
    signed_infos = models.signup_project.objects.filter(project_id=pid, type=type)
    signed_info = []
    if editboolean:                
        for info in signed_infos:
            name = models.user.objects.get(id=info.user_id).realname
            signed_info.append(name)
    else:
        for info in signed_infos:
            signed_uid = models.user.objects.get(id=info.user_id).id
            signed_info.append(signed_uid)
        if current_uid in signed_info:
            signed_info = 1
        else:
            signed_info = 0
    print signed_info
    return signed_info
        
def project_feedback(request):  #也可以写在detail里，这样更清晰
    try:
        request.session['id']
    except:
        return HttpResponseRedirect('/login')
    if request.method == 'POST':
        form = feedbackForm(request.POST)
        if form.is_valid():
            pid = form.cleaned_data['pid']
            mid = form.cleaned_data['mid']
            content = form.cleaned_data['content']
        else:
            pid = form.cleaned_data['pid']
            link = '/detail/' + str(pid)
            return HttpResponseRedirect(link)
        f = models.project_feedback(project_id=pid, feedback_member_id=mid, content=content, feedback_date=datetime.datetime.now())
        f.save()
        #下面是给该项目的所有负责人发提醒
        fb_name = models.user.objects.get(id=mid).realname
        fb_pro_name = models.project.objects.get(id=pid).project
        fb_content = fb_name + u'对"' + fb_pro_name + u'"发表了一条反馈, 请到该项目详情页进行查看'
        m = models.public_message(project=pid, publisher=mid, 
                                  content=fb_content, type_p="message", 
                                  publication_date=datetime.datetime.now(), isactived=4)
        m.save()
        messageid = public_message.objects.filter(publisher=mid).order_by("-id")[0].id
        p = project.objects.get(id=pid)
        leaderlist = (p.leader_p_id, p.designer_p_id, p.tester_p_id, 
                      p.business_man_id, p.operator_p_id, p.customer_service_id)
        adressee = []
        ppmessage = []
        for i in leaderlist:
            if i and i not in adressee:
                adressee.append(i)
                ppmessage.append(models.project_user_message(userid_id=i, messageid_id=messageid,
                                                         project_id=pid, isactived=1))
        models.project_user_message.objects.bulk_create(ppmessage)
        
        link = '/detail/' + str(pid)
        return HttpResponseRedirect(link)
        
"""
存储消息时，在public_message中isactived=4,
表示存储的是反馈信息
"""            
def feedback_comment(request):
    try:
        request.session['id']
    except:
        return HttpResponseRedirect('/login')
    if request.method == 'POST':
        form = feedbackCommentForm(request.POST)
        if form.is_valid():
            pid = form.cleaned_data['pid']
            feedbackid = form.cleaned_data['feedbackid']
            replymid = form.cleaned_data['replymid']
            comment = form.cleaned_data['comment']
        else:
            link = '/detail/' + str(pid)
            return HttpResponseRedirect(link)
        fc = models.project_feedback_comment(feedbackid_id=feedbackid, feedback_member_c_id=replymid, comment=comment, 
                                             feedback_date_c=datetime.datetime.now())
        fc.save()
        #有人回复后,反馈人会收到一个提醒.
        reply_name = models.user.objects.get(id=replymid).realname
        pro_name = models.project.objects.get(id=pid).project
        reply_message = reply_name + u'回复了你对"' + pro_name + u'"的反馈, 快到项目详情页面查看吧!'
        m = models.public_message(project=pid, publisher=replymid, 
                                  content=reply_message, type_p="message", 
                                  publication_date=datetime.datetime.now(), isactived=4)
        m.save()
        feedback_id = models.project_feedback_comment.objects.filter(feedback_member_c_id=replymid).order_by("-id")[0].feedbackid_id
        replyTo_id = models.project_feedback.objects.get(id=feedback_id).feedback_member_id
        messageid = public_message.objects.filter(publisher=replymid).order_by("-id")[0].id
        pum = models.project_user_message(userid_id=replyTo_id, messageid_id=messageid, project_id=pid, isactived=1)
        pum.save()
        
        link = '/detail/' + str(pid)
        return HttpResponseRedirect(link)
        
# def show_person(request):
#     roles = request.GET['role']
#     keys = {"tes":1, "dev":2, "pro":3, "sal":12, "ope":8, "com":7}

#     if roles == 'dev':
#         person = models.user.objects.filter(Q(department_id=keys[roles]) | Q(department_id=4) | Q(department_id=5) | Q(department_id=13), Q(isactived=1))
#     elif roles == 'sal':
#         person = models.user.objects.filter(Q(department_id=keys[roles]) | Q(department_id=9) | Q(department_id=7), Q(isactived=1))
#     elif roles == 'ope':
#         person = models.user.objects.filter(Q(department_id=keys[roles]) | Q(department_id=3) | Q(department_id=12)| \
#             Q(department_id=9) | Q(department_id=7), Q(isactived=1))
#     else:
#         person = models.user.objects.filter(department_id=keys[roles], isactived=1)
#     person_rs = []
#     num = len(person)
#     if num == 0:
#         rrs = {"person":person_rs}
#         person_rs = json.dumps(rrs)
#         return HttpResponse(person_rs)
#     for item in person:
#         uid = item.id
#         realname = item.realname
#         dic = {'id':int(uid), 'realname':realname}
#         person_rs.append(dic)

#     rrs = {"person":person_rs}
#     person_rs = json.dumps(rrs)
#     return HttpResponse(person_rs)

def psearch(request):
    key = request.GET['key']
    role = request.GET['role']
    ptype = 0
    ptypes = {"tes":1, "dev":2, "pro":3, "sal":12, "ope":8, "com":7}
    
    if len(key) == 0:
        if role == 'dev':
            prs = models.user.objects.filter(Q(isactived=1),Q(department_id=ptypes[role])|Q(department_id=4)|Q(department_id=5)|Q(department_id=13))
        elif role == 'sal':
            prs = models.user.objects.filter(Q(department_id=ptypes[role]) | Q(department_id=9) | Q(department_id=7) | Q(department_id=6), Q(isactived=1))
        elif role == 'ope':
            prs = models.user.objects.filter(Q(department_id=ptypes[role]) | Q(department_id=3) | Q(department_id=12)| \
                Q(department_id=9) | Q(department_id=7) | Q(department_id=6), Q(isactived=1))
        else:
            prs = models.user.objects.filter(department_id=ptypes[role], isactived=1)
    else:
        if role == 'dev':
            prs = models.user.objects.filter(Q(realname__contains=key), Q(isactived=1), Q(department_id=ptypes[role])|Q(department_id=4)|Q(department_id=5)|Q(department_id=13))
        elif role == 'sal':
            prs = models.user.objects.filter(Q(realname__contains=key),Q(department_id=ptypes[role]) | Q(department_id=9) | Q(department_id=7) | Q(department_id=6), Q(isactived=1))
        elif role == 'ope':
            prs = models.user.objects.filter(Q(realname__contains=key),Q(department_id=ptypes[role]) | Q(department_id=3) | Q(department_id=12)| \
                Q(department_id=9) | Q(department_id=7) | Q(department_id=6), Q(isactived=1))
        else:
            prs = models.user.objects.filter(realname__contains=key, department_id=ptypes[role], isactived=1)
            
    search_rs = []
    if len(prs) > 0:
        for item in prs:
            dic = {'id':item.id, 'realname':item.realname}
            search_rs.append(dic)
        rrs = {"person":search_rs}
        search_rs = json.dumps(rrs)
    else:
        rrs = {"person":search_rs}
        search_rs = json.dumps(rrs)
        print search_rs
    return HttpResponse(search_rs)

#通用头
def user_info(request):
    result={}
    try:
        if request.session['username']:
            projectlist = models.project.objects.filter()
            project_user_list = models.project_user.objects.filter(username__username = request.session['username'])
            projectids = []
            for p in project_user_list:
                projectids.append(p.project.id) 
            projectlist = projectlist.filter(pk__in = projectids)       
            res = projectlist.exclude(Q(status_p = u'已上线') | Q(status_p = u'已暂停') | Q(status_p = u'运营推广')).order_by("-id")
            pro_num=res.count()
            result['pro_num'] = pro_num
   
            userid = request.session['id']
            if request.user.has_perm('project.change_project_delay'):
                messsage = project_user_message.objects.filter(Q(userid_id = userid) | Q(isactived = 0))
            else:
                messsage = project_user_message.objects.filter(userid_id = userid).exclude(isactived = 0)
            message_num = messsage.count()
            result['message_num'] = message_num
                       
            username = request.session['username']
            realname = request.session['realname']
            uid = request.session['id']
            result['username'] = username
            result['realname'] = realname    
            result['uid'] = uid  
    except KeyError:
            result['pro_num'] = 0
            result['message_num'] = 0
            result['username'] = 'GUEST'
            result['realname'] = 'GUEST' 
    rs = json.dumps(result)
    return HttpResponse(rs)
#homepage
def personal_homepage(request):
    try:
        request.session['username']
        projectlist = models.project.objects.filter()
        project_user_list = models.project_user.objects.filter(username__username = request.session['username'])
    except KeyError:
        return HttpResponseRedirect("/nologin")
    #设计变更
    changetag = edittag = delaytag = pausetag = deletetag = pm = 0
    if request.user.has_perm('project.change_public_message'):
        changetag = 1
    #编辑
    if request.user.has_perm('project.change_project'):
        edittag = 1
    #延期申请权限
    if request.user.is_authenticated():
        userid1 = request.session['id']
    if request.user.has_perm('project.add_project_delay'):
        delaytag = 1
    #暂停
    if request.user.has_perm('project.delete_project'):
        pausetag = 1  
    #删除
    if request.user.has_perm('project.delete_project'):
        deletetag = 1 
    if request.user.has_perm("auth.change_permission"):
        pm = 1
    projectids = []
    #用于存储相应项目成员
    relateduser={}
    ifscore = {}
    for p in project_user_list:
        projectids.append(p.project.id)
        user = models.project_user.objects.filter(project = p.project.id)
        uname=''
        for u in user:
            pattern = re.compile(u.username.realname)
            match = pattern.search(uname)
            if not match:
                uname = uname + ' ' + u.username.realname
        relateduser[p.project.id] = uname
        # 标致项目是否需要打分，结合前端判断当前用户是否显示“打分”操作
        ifscore[p.project.id] = 0
        try:
            s = models.pro_score.objects.get(project = p.project.id).pm_done
            if s:
                ifscore[p.project.id] = 1
        except:
            pass 
    projectlist = projectlist.filter(pk__in = projectids)
    result = projectlist.exclude(Q(status_p = u'已上线') | Q(status_p = u'已暂停') | Q(status_p = u'运营推广')).order_by("-id")   
    result1 = projectlist.exclude(~Q(status_p = u'已上线')& ~Q(status_p = u'运营推广')).order_by("-id")
    #判断项目是否显示橙色和选中相应项目负责人
    rendering = {}
    for org in result:
        l = []
        if org.status_p !=u'已暂停' and org.status_p != u'已上线':
            time = datetime.datetime.now()
            nowtime=time.strftime("%Y-%m-%d") 
            if org.expect_launch_date:
                expect_date = org.expect_launch_date
                if  expect_date.strftime("%Y-%m-%d ") < nowtime:
                    stu_col = "style=background-color:#ff9933"
                else:
                    stu_col =''
                l.append(stu_col)
            else:
                stu_col =''
                l.append(stu_col) 
        business_man = design = prom = tester = operator = customer_service = ''
        if org.type_p == u'产品':
            if org.status_p == u'需求讨论中' or org.status_p == u'设计中' or org.status_p == u'设计完成':                
                design =  "style=color:#339966;font-weight:bold"    
        else:
            if org.status_p == u'需求讨论中':
                business_man =  "style=color:#339966;font-weight:bold"
            if org.status_p == u'设计中' or org.status_p == u'设计完成':
                design =  "style=color:#339966;font-weight:bold"
        if org.status_p == u'开发中':
            prom = "style=color:#339966;font-weight:bold"
        if org.status_p == u'测试中':
            tester = "style=color:#339966;font-weight:bold"
        if org.status_p == u'运营推广':
            operator = "style=color:#339966;font-weight:bold"
        l.append(business_man)
        l.append(design)
        l.append(prom)
        l.append(tester)
        l.append(operator)
        l.append(customer_service)
        rendering[org.id]= l    
    """分页"""
    paginator = Paginator(result1, 25)
    page = request.GET.get('page')
    try:
        projectobj = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        projectobj = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        projectobj = paginator.page(paginator.num_pages)
    #message
    userid = request.session['id']
    dealdelay = 0
    countdelay = 0
    if request.user.has_perm('project.change_project_delay'):
        dealdelay = 1
        delays = project_delay.objects.filter(result__isnull=True,).order_by('apply_date')
        countdelay = delays.count()
        tests= project_user_message.objects.filter(Q(isactived ='0') |Q(userid_id = userid1))
    else:
        tests= project_user_message.objects.filter(userid_id = userid1).exclude(isactived = 0)
    lists = []
    messagess = []
    for test in tests:
        lists.append(test.messageid_id)
    messagess = public_message.objects.filter(pk__in = lists).filter(type_p = "message").order_by('-id')  
    count = messagess.count()
    messages = messagess[:4]   
    return render_to_response('personal_homepage.html', \
        {'projectobj':projectobj, 'result':result, 'result1':result1, 'relateduser': relateduser, 'ifscore':ifscore, 'rendering': rendering, 'messages': messages, \
         'count':count, 'dealdelay':dealdelay, 'changetag':changetag, 'edittag':edittag, 'delaytag':delaytag, 'pausetag':pausetag, \
         'deletetag':deletetag, 'pm':pm, 'userid1':userid1,'countdelay':countdelay})
def deleteproject(request,pid,url):
    delpro=get_object_or_404(project,pk=int(pid))
    delpro.delete()
    return HttpResponseRedirect(url)
def pauseproject(request, pid, url):
    pausepro = get_object_or_404(project, pk = int(pid))
    pausepro.status_p ='已暂停'
    pausepro.save()
    return HttpResponseRedirect(url)
"""
存储消息时，跟消息对应的是项目的成员，项目经理不属于成员，所以
在public_message中isactived=5,
project_user_message 中isactived=0，表示发送给项目经理的
"""
def delayproject(request, url):
    if request.method == 'POST':
        form = delayprojectForm(request.POST)
        if form.is_valid():
            delayid = form.cleaned_data['delayid']
            delay_date = form.cleaned_data['delay_date']
            delay_reason = form.cleaned_data['delay_reason']
            delpro = models.project.objects.get(id=delayid)
            uid = delpro.leader_p
            protitle = delpro.project
            delay_name = uid.realname
            uuid = request.session['id'] 
            delay_p = project_delay(application = uid, project_id = delayid, delay_to_date = delay_date, \
                apply_date = datetime.datetime.now(), title = protitle, reason = delay_reason, isactived = 1)
            delay_p.save()
            #向project_message中isactived=5和project_user_message isactived=0表中分别插入一条消息，数字分别标记发送给项目经理的信息
            remind_con = protitle + u' : ' + delay_name + u'申请延期，请及时处理!'
            delay_remind = public_message(project = delayid, publisher = uuid, content = remind_con, type_p = "message",\
                           publication_date = datetime.datetime.now(), isactived = 5) 
            delay_remind.save()
            message = public_message.objects.filter(project=delayid).order_by("-id")[0]
            delay_pm_message = project_user_message(userid_id = uuid, messageid_id = message.id, \
                    project_id = delayid, isactived = 0)
            delay_pm_message.save()                  
    return HttpResponseRedirect(url)
def changedesign(request, url):         
    if request.method == 'POST':
        form = changedesignForm(request.POST)
        if form.is_valid():
            changeid = form.cleaned_data['changeid']
            cont = form.cleaned_data['cont'].replace('\r\n','<br/> ')
            dpath = form.cleaned_data['dpath'].replace('\r\n','<br/> ')
            chd = models.project.objects.get(id = changeid)
            uid = request.session['id']
            string = chd.project+u' : ' + '<br/> ' +cont + '<br/> ' + dpath
            pub_message = public_message(project = changeid, publisher = uid, content = string, type_p = "message",\
             publication_date = datetime.datetime.now(), isactived = "1")
            pub_message.save()
            related_user = models.user.objects.filter(project_user__project_id = changeid).distinct()
            message = public_message.objects.filter(project=changeid).order_by("-id")[0]            
            for i in related_user:
                uid = i.id
                megid = message.id
                pro_u_message = project_user_message(userid_id = uid, messageid_id = megid, \
                    project_id = changeid, isactived = '1')
                pro_u_message.save()           
    return HttpResponseRedirect(url)
    #return render_to_response('personal_homepage.html', {'form': form})

#资源管理
def judge(request):
    try:
        if request.session['username']:
            username = request.session['username']
        Position_level = models.user.objects.get(username=\
        username).Position_level
        if Position_level == '1' or request.user.has_perm('project.change_user'):
            return redirect('/show_user/')
        else:
            return redirect('/show_source/')
    except KeyError:
        return redirect('/nologin/')
def show_source(request):
    try:
        if request.session['username']:
            username = request.session['username']
            department_id = models.user.objects.get(username=\
            username).department_id
        department_id = department_id
        department = models.department.objects.get(id=\
        department_id).department
        department_list = models.department.objects.all()
        department_list = department_list.exclude(Q(department='blank'))
        level_1_list = models.user.objects.filter(department_id=\
        department_id, Position_level="1")
        level_2_list = models.user.objects.filter(department_id=\
        department_id, Position_level="2")
        level_3_list = models.user.objects.filter(department_id=\
        department_id, Position_level="3")
        return render_to_response('show_source.html', locals())
    except KeyError:
        return redirect('/nologin/')

@csrf_exempt
def show_user2(request):
    department = request.POST['department']
    if department == '请选择':
        department_id = 0
    else:
        depart = models.department.objects.all()
        departdic = {}
        for item in depart:
            departdic[item.department] = item.id
        department_id = departdic[department]
    level_1_list = models.user.objects.filter(department_id=\
    department_id, Position_level="1")
    level_2_list = models.user.objects.filter(department_id=\
    department_id, Position_level="2")
    level_3_list = models.user.objects.filter(department_id=\
    department_id, Position_level="3")
    department_list = models.department.objects.all()
    department_list = department_list.exclude(Q(department='blank'))
    return render_to_response('show_source.html', locals())

@csrf_exempt
def show_user(request):
    try:
        if request.session['username']:
            username = request.session['username']
            department_id = models.user.objects.get(username=\
            username).department_id
        department_id = department_id
        department = models.department.objects.get(id=\
        department_id).department
        if request.method == 'POST':
            department = request.POST['department']
            if department == '请选择':
                department_id = 0
            else:
                depart = models.department.objects.all()
                departdic = {}
                for item in depart:
                    departdic[item.department] = item.id
                department_id = departdic[department]
        else:
            department_id = department_id
        level_list = models.user.objects.filter(department_id=\
        department_id)
        level_1_list = models.user.objects.filter(department_id=\
        department_id, Position_level="1")
        level_2_list = models.user.objects.filter(department_id=\
        department_id, Position_level="2")
        level_3_list = models.user.objects.filter(department_id=\
        department_id, Position_level="3")
        department_list = models.department.objects.all()
        department_list = department_list.exclude(Q(department='blank'))
        return render_to_response('sourcemanage.html', locals())
    except KeyError:
        return redirect('/nologin/')

@csrf_exempt
def Insert_user(request, id1, id2, id3):
    if request.session['username']:
        username = request.session['username']
        department_id = models.user.objects.get(username=\
        username).department_id
    department_id = department_id
    department = request.POST['department']
    if department == '请选择':
        department_id = 0
    else:
        depart = models.department.objects.all()
        departdic = {}
        for item in depart:
            departdic[item.department] = item.id
        department_id = departdic[department]
    if id1 == '1':
        id = request.POST['level_1']
        user = models.user.objects.filter(department_id=\
        department_id, id=id).update(Position_level='1')
    elif id1 == '2':
        id = request.POST['level_2a']
        user = models.user.objects.filter(department_id=department_id, \
        id=id).update(Position_level='2')
    elif id1 == '3':
        id = request.POST['level_3a']
        user = models.user.objects.filter(department_id=department_id, \
        id=id).update(Position_level='3')
    elif id1 == '4':
        id = request.POST['level_1']
        user = models.user.objects.filter(department_id=department_id, \
        id=id).update(Position_level='0')
    elif id1 == '5':
        user = models.user.objects.filter(department_id=department_id, \
        id=id2).update(Position_level='0')
    elif id1 == '6':
        user = models.user.objects.filter(department_id=department_id, \
        id=id2).update(Position_level='0')
    elif id1 == '7':
        id = request.POST['level_1']
        if(int(id)==request.session['id']):
            return HttpResponseRedirect("/noperm")
        else:
            user = models.user.objects.get(department_id=department_id, \
            id=id)
            user.delete()
    elif id1 == '8':
        if(int(id2)==request.session['id']):
            return HttpResponseRedirect("/noperm")
        else:
            user = models.user.objects.get(department_id=department_id, \
            id=id2)
            user.delete()
    elif id1 == '9':
        if(int(id2)==request.session['id']):
            return HttpResponseRedirect("/noperm")
        else:
            user = models.user.objects.get(department_id=department_id, \
            id=id2)
            user.delete()
    elif id1 == '10':
        user = models.user.objects.filter(department_id=department_id, \
        id=id3).update(Position_level='0')
        user = models.user.objects.filter(department_id=department_id, \
        id=id2).update(Position_level='2')
    elif id1 == '11':
        user = models.user.objects.filter(department_id=department_id, \
        id=id3).update(Position_level='0')
        user = models.user.objects.filter(department_id=department_id, \
        id=id2).update(Position_level='3')
    elif id1 == '12':
        user = models.user.objects.filter(department_id=department_id, \
        id=id3).update(Position_level='0')
        user = models.user.objects.filter(department_id=department_id, \
        id=id2).update(Position_level='1')
    return redirect('/show_user/')
#延期
def delay(request):

    if not request.user.is_authenticated():
        return HttpResponseRedirect("/nologin")

    if not request.user.has_perm('project.change_project_delay'):
        return HttpResponseRedirect("/noperm")

    delays = project_delay.objects.filter(isactived__isnull= False).order_by('-id')
    global  projectobj
    paginator = Paginator(delays, 25)
    page = request.GET.get('page')
    try:
        projectobj = paginator.page(page)
    except PageNotAnInteger:
        #If page is not an integer, deliver first page.
        projectobj = paginator.page(1)
    except EmptyPage:
        #If page is out of range (e.g. 9999), deliver last page of results.
        projectobj = paginator.page(paginator.num_pages)
    return render_to_response('delay.html', RequestContext(request, {'projectobj': projectobj}))

#公告
def notice(request):
    global search_key
    search_key=''
    if request.method == 'POST':  # 如果是post请求
        wds = request.POST
        try:
            noticetext = wds['wd']
            search_key=noticetext
            notices = public_message.objects.filter(content__icontains=noticetext).filter(type_p="notice").order_by("-id")

        except Exception:
            notices = public_message.objects.filter(type_p="notice").order_by("-id")
    else:  # Get请求
        wds = request.GET
        try:
            search_key = wds['search_key']
            notices = public_message.objects.filter(type_p="notice").filter(content__icontains=search_key).order_by("-id")
        except Exception:
            notices = public_message.objects.filter(type_p="notice").order_by("-id")
    global  projectobj
    paginator = Paginator(notices, 25)
    page = request.GET.get('page')
    try:
        projectobj = paginator.page(page)
    except PageNotAnInteger:
    #If page is not an integer, deliver first page.
        projectobj = paginator.page(1)
    except EmptyPage:
    #If page is out of range (e.g. 9999), deliver last page of results.
        projectobj = paginator.page(paginator.num_pages)
    return render_to_response('notice.html', RequestContext(request, {'projectobj': projectobj,'search_key':search_key}))

@csrf_exempt

#历史消息
def historymessage(request):
    if not request.user.is_authenticated():
        return HttpResponseRedirect("/nologin")

    global search_key
    search_key=''
    # 查询与用户相关的消息
    if request.session['id']:
        useid = request.session['id']
    if request.user.has_perm('project.change_project_delay'):
        tests= project_user_message.objects.filter(Q(isactived = 0) | Q(userid_id = useid))
    else:
        tests= project_user_message.objects.filter(userid_id = useid).exclude(isactived = 0)
    lists = []
    for test in tests:
        lists.append(test.messageid_id)
    if request.method == 'POST':  # 如果是post请求
        wds = request.POST
        try:
            messagetext = wds['wd']
            search_key= messagetext
            messages = public_message.objects.filter(pk__in=lists).filter(content__icontains=messagetext).filter(type_p="message").order_by('-id')
        except Exception:
            messages = public_message.objects.filter(pk__in=lists).filter(type_p="message").order_by('-id')
    else:  # Get请求
        wds = request.GET
        try:
            search_key = wds['search_key']
            messages = public_message.objects.filter(pk__in=lists).filter(type_p="message").filter(content__icontains=search_key).order_by('-id')
        except Exception:
            messages = public_message.objects.filter(pk__in=lists).filter(type_p="message").order_by('-id')
    global  projectobj
    paginator = Paginator(messages, 25)
    page = request.GET.get('page')
    try:
        projectobj = paginator.page(page)
    except PageNotAnInteger:
    #If page is not an integer, deliver first page.
        projectobj = paginator.page(1)
    except EmptyPage:
        projectobj = paginator.page(paginator.num_pages)
    return render_to_response('historymessage.html', RequestContext(request, {'projectobj': projectobj,'search_key':search_key}))

#拒绝
def refuse(request):
    if request.method == 'POST':

        form = TestForm(request.POST)
        if form.is_valid():
            delayid = form.cleaned_data['delayid']
            reason = form.cleaned_data['reason']
            refusedelay = project_delay.objects.get(id=delayid)
            project_id = refusedelay.project_id
            deltitle = refusedelay.title
            string = deltitle+u"申请延期被拒绝，理由"+reason
            #delpro=models.project.objects.get(id=delayid)
            if request.session['id']:

                useid = request.session['id']
                pub_message = public_message(project=project_id, publisher=useid, content=string, \
                    type_p="message", publication_date=datetime.datetime.now(), delay_status="已拒绝", isactived="1")
            #refusedelay.reason = reason
                refusedelay.result = "已拒绝"
                refusedelay.isactived = 0
                refusedelay.save()
                pub_message.save()
                related_user = models.user.objects.filter(project_user__project_id=project_id).distinct()
                message = public_message.objects.filter(project=project_id).order_by("-id")[0]
            all_uesr_message = []
            for i in related_user:
                uid = i.id
                megid = message.id
                pro_u_message = project_user_message(userid_id=uid, messageid_id=megid, project_id=project_id, isactived='1')
                all_uesr_message.append(pro_u_message)
            project_user_message.objects.bulk_create(all_uesr_message)
    return HttpResponseRedirect('/delay/')

#接受
def approve(request):
    if request.method == 'POST':
        form = Approveform(request.POST)
        if form.is_valid():
            delayid1 = form.cleaned_data['delayid1']
            approvedelay = project_delay.objects.get(id=delayid1)
            project_id = approvedelay.project_id
            deltitle = approvedelay.title
            delaydate= approvedelay.delay_to_date
            del_to_date = str(delaydate)
            string = deltitle + u"延期至：" + del_to_date
            pro = project.objects.get(id=project_id)
            pro.expect_launch_date = delaydate
            pro.save()
            #delpro=project_delay.objects.get(id=delayid1)
        if request.session['id']:
            useid = request.session['id']
            pub_message = public_message(project=project_id, publisher=useid, content=string, type_p="notice", \
                publication_date=datetime.datetime.now(), delay_status="已批准", isactived="1")
            #approvedelay.reason = reason

            approvedelay.isactived = 0
            approvedelay.result = "已批准"
            approvedelay.save()
            pub_message.save()
    return HttpResponseRedirect('/delay/')


#负责人确认消息
def confirmmessage(request):
    if request.session['id']:
        useid = request.session['id']
    if request.method == 'POST':
        form = ConmessageForm(request.POST)
        if form.is_valid(): 
            #public_message修改状态已确认
            messageid = form.cleaned_data['conmessageid']
            conmessage = public_message.objects.get(publisher=useid, id=messageid)
            conmessage.delay_status = "已确认"
            reconmessage = conmessage
            conmessage.save()
            #project_operator_bussniess_message修改状态、插入确认时间
            #如果public_message的isactived为2，就是设计需要确认
            #如果public_message的isactived为3，就是已发测试版本需要确认
            if  reconmessage.isactived==3:
                pmessages = project_operator_bussniess_message.objects.filter(userid_id=useid , project_id = conmessage.project ,\
                                                                  status = "项目未验收" )
                for pmessage in pmessages:
                    pmessage.check_date = datetime.datetime.now()
                    pmessage.status = "项目已验收"
                    pmessage.save()
            if reconmessage.isactived==2:
                pmessages = project_operator_bussniess_message.objects.filter(userid_id=useid , project_id = conmessage.project ,\
                                                                  status = "未确认设计" )
                for pmessage in pmessages:
                    pmessage.confirm_design_date = datetime.datetime.now()
                    pmessage.status = "已确认设计"
                    pmessage.save()
    return HttpResponseRedirect('/historymessage/')


#删除历史消息
def deletehistory(request):
    if request.session['id']:
        useid = request.session['id']
    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            messageid = form.cleaned_data['messageid']
            if request.user.has_perm('project.change_project_delay'): 
                usermessage = project_user_message.objects.get(messageid_id=messageid)
            else:
                usermessage = project_user_message.objects.get(userid_id=useid, messageid_id=messageid)
            usermessage.delete()
    tests = project_user_message.objects.filter(userid_id=useid)
    lists = []
    for test in tests:
        lists.append(test.messageid_id)
    return HttpResponseRedirect('/historymessage/')

#删除公告
def deletenotice(request):
    if request.session['id']:
        useid = request.session['id']
    if request.method == 'POST':
        form = NoticeForm(request.POST)
        if form.is_valid():
            noticeid = form.cleaned_data['noticeid']
            usernotice = project_user_message.objects.get(userid_id=useid, messageid_id=noticeid)
            usernotice.delete()
    tests = project_user_message.objects.filter(userid_id=useid)
    lists = []
    for test in tests:
        lists.append(test.messageid_id)
    return HttpResponseRedirect('/notice/')

#清空历史消息
def emptyehistory(request):
    if request.session['id']:
        useid = request.session['id']
    tests = project_user_message.objects.filter(Q(userid_id=useid) | Q(isactived = 0))
    print tests
    if request.method == 'POST':
        for test in tests:
            test.delete()
    return HttpResponseRedirect('/historymessage/')

#项目统计详情页
def statistics_detail(request): 
    if not request.user.is_authenticated():
        return HttpResponseRedirect("/nologin")
    pm = 0
    if request.user.has_perm("auth.change_permission"):
        pm = 1
    pros = models.project_statistics.objects.filter(isactived = 1).values_list("project_id", flat=True)
    sproject_info = models.project_module.objects.filter(project__in = pros)
    if request.method == "POST":
        form = sdetailForm(request.POST)
        if form.is_valid():
            module_p = form.cleaned_data['module_p']
            kw = form.cleaned_data['kw']
    else:
        kw=''
        module_p=''
        try:
            kw = request.GET["kw"]
            module_p = request.GET["module_p"]
        except Exception:
            pass
    sproject_info = sproject_info.filter(project__project__contains = kw, module__module_name__contains = module_p)
    dic_list = []
    for item in sproject_info:
        all_sp = []       
        total = models.project_statistics.objects.filter(project_id=item.project.id).order_by("total")[0]
        dic = {'id':item.project.id, "total":total.total, "module":item.module.module_name}
        dic_list.append(dic)            
    """分页"""
    paginator = Paginator(sproject_info, 25)
    page = request.GET.get('page')
    try:
        projectobj = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        projectobj = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        projectobj = paginator.page(paginator.num_pages)   
    return render_to_response('statistics_detail.html', RequestContext(request, {'sproject_info': sproject_info,\
     "dic_list":dic_list, "projectobj":projectobj, "kw":kw, "module_p":module_p, 'pm':pm}))

def sdropdown(request, pid):
    total = models.project_statistics.objects.filter(project_id=pid, isactived = 1).order_by("total")
    sdetail = {}
    all_sp = []
    for s in total:        
        sdetail = {"sql":s.id, "item":s.item, "num":s.total}
        all_sp.append(sdetail)          
    return HttpResponse(json.dumps(all_sp))

def statistics_operate(request):
    if request.method == 'POST':
        form = addmoduleForm(request.POST)
        if form.is_valid():
            bulk_sid = form.cleaned_data['bulk_sid']
            modulename = form.cleaned_data['modulename'] 
            add_module = models.module.objects.get(module_name = modulename)
            mid = add_module.id                      
            bulk_sid = bulk_sid.split(",")
            all_pro_module = []
            for pid in bulk_sid:
                if pid:
                    pro_module = models.project_module.objects.filter(project_id = pid).update(module = mid)
        else:
            form = addmoduleForm()
    return HttpResponseRedirect('/sdetail/')

def show_slist(request):
    if not request.user.is_authenticated():
        return HttpResponseRedirect("/nologin")
    pros = models.project_statistics.objects.filter(isactived = 1).values_list("project_id", flat=True)
    module_info = models.module.objects.all()
    modele_list = []
    for item in module_info:
        tempdict = {}
        mproject = models.project_module.objects.filter(module_id=item.id, project__in = pros).order_by('-id')[0:16]
        tempdict = {'id':item.id, 'name':item.module_name, 'plist':mproject}
        modele_list.append(tempdict)

    print modele_list
    return render_to_response('statistics_list.html', {'module_list':modele_list}, context_instance=RequestContext(request))

def sdata(request, pid):
    sqlnum = models.project_statistics_result.objects.filter(project_id=pid).distinct().values_list('sql_id')
    sql_ids = []
    for s in sqlnum:
        sql_ids.append(s[0])
    sdata = {}
    for sid in sql_ids:
        labels = []
        total = []
        datas = models.project_statistics_result.objects.filter(sql_id=sid).order_by("date")
        for i in range(0, len(datas)+1, 30):
            try:
                labels.append(str(datas[i].date))
                total.append(datas[i].statistical_result)
            except:
                pass                
        if len(labels)==1:
            labels.append("")
        sdata[sid] = {'labels': labels, 'total': total}
           
    return HttpResponse(json.dumps(sdata))

def signup_project(request, type, uid, pid):
    print datetime.datetime.now()
    signup_info = models.signup_project(project_id=int(pid), user_id=int(uid), type=type, time=datetime.datetime.now(), isactived=1)
    signup_info.save()
    
    return HttpResponse("success")

def score(request, pid):
    try:         #没登录的去登录页面
        request.session['id']
    except:
        return HttpResponseRedirect('/login')
    pro = models.project.objects.get(id=int(pid))
    try:
        ps = models.pro_score.objects.get(project_id=int(pid))
        pro_actual_score = "未评" if isNone(ps.p_actual_score) else ps.p_actual_score
        ispm_done = ps.pm_done
    except:
        pro_actual_score = "未评"
        ispm_done = 1
    devs = models.user.objects.filter(Q(project_user__project_id=pid), Q(project_user__roles=1), Q(department_id=2) | Q(department_id=4) | Q(department_id=5) | Q(department_id=13))
    p_role = []
    dep_id = [[1,2], [3,0]]
    for item_id in dep_id:
        p_role.append(models.user.objects.filter(project_user__project_id=pid, department_id=item_id[0], project_user__roles=item_id[1]))
    scoreboolean = 0
    if ((request.user.has_perm('auth.change_permission') or request.session['id']==pro.leader_p_id) and ispm_done): #and比or优先
                    scoreboolean = 1 #判断是否有打分权限,项目经理或PM并且尚未提交打分
    related_user = {'dev': devs,
              'pd': p_role[1],
              'qa': p_role[0]}
    user_info = {}
    for section, users in related_user.items():
        user_info[section] = []
        for user in users:
            try:
                sobj = models.user_score.objects.get(user_id=user.id, project_id=pid)
                user_info[section].append([user,sobj])
            except:
                user_info[section].append([user,''])
     
    result = {'pro': pro,
              'pro_s': pro_actual_score,
              'dev': user_info['dev'],
              'pd': user_info['pd'],
              'qa': user_info['qa'],
              'scorebool': scoreboolean,
              'done_flag': ispm_done,
              }
    return render_to_response('score.html',{'res': result})

def scoreuser(request, pid, flag):
    datas = json.loads(request.POST.get('datas',False))
    uscores = []
    for key,value in datas.items():
        print key, value
        try:
            models.user_score.objects.filter(user_id=key, project_id=pid).delete()
        finally:
            if value[0]:#因为数据库中分数是int型，如果为空存储时会报错
                uscores.append(models.user_score(user_id=key, project_id=pid, 
                                             u_actual_score=value[0], 
                                             u_actual_dpt=value[1], upd_time=datetime.datetime.now()))
            else:
                uscores.append(models.user_score(user_id=key, project_id=pid,                                              
                                             u_actual_dpt=value[1], upd_time=datetime.datetime.now()))
    models.user_score.objects.bulk_create(uscores)

    if(int(flag)==0):
        try:
            ps = models.pro_score.objects.get(project_id=pid)
            ps.pm_done = 0
            ps.save()
        except:
            return HttpResponse(json.dumps({0:"请先找架构组给项目评分后才可以提交最终评分！"}))
    return HttpResponse(json.dumps({1:"success"}))

def myscore(request, userid='', year='c'):
    try:         #没登录的去登录页面
        uid = request.session['id']
    except:
        return HttpResponseRedirect('/login')
    if userid:
        uid = userid
    print year
    if year == 'a':  #全部积分
        sobj = models.user_score.objects.filter(user_id=uid)
        total_score = models.user_score.objects.filter(user_id=uid).aggregate(total=Sum('u_actual_score'))
    else:  #当年积分
        sobj = models.user_score.objects.filter(user_id=uid, upd_time__gte='2017-01-01')
        total_score = models.user_score.objects.filter(user_id=uid, upd_time__gte='2017-01-01').aggregate(total=Sum('u_actual_score'))
    uscore = {} #通过user_score表的外链就可以访问到对应的project对象
    for obj in sobj:
        try:
            uscore[obj] = models.pro_score.objects.get(project_id=obj.project_id).pm_done
        except:
            uscore[obj] = 1
    whose = models.user.objects.get(id=uid)
    result = {'uscore': uscore,
              'owner': whose,
              'total': total_score}    
    return render_to_response('myscore.html',{'res': result})
  

def scorelist(request):
    try:         #没登录的去登录页面
        uid = request.session['id']
    except:
        return HttpResponseRedirect('/login')  
    slist = {}
    dslist = {'1':[],'2':[], '3':[], '4':[], '5':[]} #1:测试;2.WEB;3.产品;4.客户端;5.IT
    dep_id = [1,2,3,4,5]
    users = models.user_score.objects.values('user').distinct()
    for user in users:
        try:
            uobj = models.user.objects.get(id=user['user'], isactived=1)
            slist[uobj] = models.user_score.objects.filter(user_id=user['user'], upd_time__gte='2017-01-01').aggregate(total=Sum('u_actual_score'))
            if not slist[uobj]['total']:
                slist[uobj]['total'] = 0
        except:
            pass   #如果离职人员isactived=0就不必显示在分数列表了
    slist = sorted(slist.iteritems(), key=lambda d:d[1], reverse = True)
    for item in slist:
        if item[0].department_id in dep_id:
            dslist[str(item[0].department_id)].append(item)
        else:
            pass
    for i in dep_id:
        num = len(dslist[str(i)])#部门人数小于4都是只有加油区,没有光荣区
        good = num*85*30/10000
        if num*5%100>0:
            weak = num*5/100+1
        else:
            weak = num*5/100
        dslist[str(i)].append({'flower':good, 'rocket':weak})
    
    print dslist
    result = {'slist': slist, 'dslist': dslist}
    return render_to_response('scorelist.html',{'res':result})

def dscorelist(request):
    try:         #没登录的去登录页面
        uid = request.session['id']
    except:
        return HttpResponseRedirect('/login')  
    slist = {}

def initdata(request):
    #auth_group
    group1 = Group(id=1,name='项目经理权限--新建、编辑、删除、暂停、延期处理、发布相似')
    group1.save()
    group2 = Group(id=2,name='资源管理权限--编辑部门人员')
    group2.save()
    group3 = Group(id=3,name='产品部门权限--设计变更')
    group3.save()
    group4 = Group(id=4,name='项目负责人权限--延期申请、编辑')
    group4.save()
    group5 = Group(id=5,name='产品负责人权限--编辑')
    group5.save()
    group6 = Group(id=6,name='测试负责人权限--编辑')
    group6.save()  
    group7 = Group(id=7,name='业务负责人权限--编辑')
    group7.save() 
    group8 = Group(id=8,name='运营负责人权限--编辑')
    group8.save() 
    group9 = Group(id=9,name='客服负责人权限--编辑')
    group9.save() 
    #auth_group_permissions
    group1.permissions.add(25)
    group1.permissions.add(26)
    group1.permissions.add(27)
    group1.permissions.add(35)
    group1.permissions.add(5)
    group2.permissions.add(23)
    group3.permissions.add(32)
    group4.permissions.add(34)
    group4.permissions.add(26)
    group5.permissions.add(26)
    group6.permissions.add(26)
    group7.permissions.add(26)
    group8.permissions.add(26)
    group9.permissions.add(26)
    #project_department
    depart1 = department(id=1,department='测试',isactived=1)
    depart1.save()
    depart2 = department(id=2,department='网站研发',isactived=1)
    depart2.save()
    depart3 = department(id=3,department='产品部',isactived=1)
    depart3.save()
    depart4 = department(id=4,department='客户端研发',isactived=1)
    depart4.save()
    depart5 = department(id=5,department='IT',isactived=1)
    depart5.save()
    depart6 = department(id=6,department='院校事业',isactived=1)
    depart6.save()
    depart7 = department(id=7,department='客服部',isactived=1)
    depart7.save()
    depart8 = department(id=8,department='市场部',isactived=1)
    depart8.save()
    depart9 = department(id=9,department='中小学事业部',isactived=1)
    depart9.save()
    depart10 = department(id=10,department='行政人事财务部',isactived=1)
    depart10.save()
    depart11 = department(id=11,department='管理部',isactived=1)
    depart11.save()
    depart12 = department(id=12,department='销售部',isactived=1)
    depart12.save()
    depart13 = department(id=13,department='项目研发部',isactived=1)
    depart13.save()
    depart100 = department(id=100,department='blank',isactived=1)
    depart100.save()   
    # module
    module1 = module(id=1,module_name='机构后台',isactived=1)
    module1.save()
    module2 = module(id=2,module_name='机构前台',isactived=1)
    module2.save()
    module3 = module(id=3,module_name='AS平台(AS运营类)',isactived=1)
    module3.save()
    module4 = module(id=4,module_name='客户端产品',isactived=1)
    module4.save()
    module5 = module(id=5,module_name='考试系统',isactived=1)
    module5.save()
    module6 = module(id=6,module_name='内部管理',isactived=1)
    module6.save()
    module7 = module(id=7,module_name='项目组产品',isactived=1)
    module7.save()    
    module8 = module(id=100,module_name='综合类',isactived=1)
    module8.save()
        
    return HttpResponse("恭喜你,初始化数据成功~")
