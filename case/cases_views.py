# coding=utf-8
<<<<<<< HEAD
from django.shortcuts import render_to_response, redirect, RequestContext,HttpResponse,get_object_or_404
=======
import datetime
from django.shortcuts import render_to_response, redirect, RequestContext,HttpResponse
>>>>>>> origin/case
from models import testcase, casemodule, category, result
from forms import searchForm
import json
from project.views import isNone
from django.db.models import Q

def case_list(request,pid):
	kwargs={}
	case = {}
	cate1 = cate2 = cate3 = categoryid = ctestmodule = 	cpriority = cauthor = \
	cexecutor = cstart_date = cend_date = cexec_status = ckeyword =  cstatue = cmold = ''
	if request.method == "POST":
		search = searchForm(request.POST)
		if search.is_valid():
			cate1 = search.cleaned_data['cate1']
			cate2 = search.cleaned_data['cate2']
			cate3 = search.cleaned_data['cate3']
			categoryid = search.cleaned_data['categoryid']
			ctestmodule = search.cleaned_data['testmodule']
			cpriority = search.cleaned_data['priority']
			cstatue = search.cleaned_data['status']
			cmold =  search.cleaned_data['mold']
			cauthor = search.cleaned_data['author']
			cexecutor = search.cleaned_data['executor']
			cstart_date = search.cleaned_data['start_date']
			cend_date = search.cleaned_data['end_date']
			cexec_status = search.cleaned_data['exec_status']
			ckeyword = search.cleaned_data['keyword']
			subset2 = list(category.objects.filter(parent_id = categoryid).values_list("id",flat=True))
			subset3 = list(category.objects.filter(parent_id__in = subset2))
			subset = list(set(subset2).union(set(subset3)))
			subset.append(categoryid)			
			if not isNone(categoryid):
				kwargs['category__in'] =  subset				
			if not isNone(cauthor):
				kwargs['author'] =  cauthor
			cmodule = testcase.objects.filter(**kwargs)
			if not isNone(cpriority):
				kwargs['priority'] = cpriority
			if not isNone(ckeyword):
				kwargs['action__contains'] = ckeyword
			cmodule = testcase.objects.filter(**kwargs)
			testmodule = casemodule.objects.filter(pk__in = cmodule.values_list("module",flat=True))
			caseresult = result.objects.filter(testcase__in = cmodule)
			if not isNone(ctestmodule):
				testmodule = testmodule.filter(m_name = ctestmodule)

			args = [Q(result = cmold) , ~Q(result = cmold)] 
			args2 = [~Q(pk__in = caseresult.values_list("testcase", flat=True).distinct()),Q(pk__in = caseresult.values_list("testcase", flat=True).distinct())]
			if not isNone(cmold) and not isNone(cstatue):
				if cmold == u"未执行":
					cmodule = cmodule.filter(args2[int(cstatue)])
				else:
					caseresult = caseresult.filter(args[int(cstatue)])
					cmodule = cmodule.filter(pk__in = caseresult.values_list("testcase", flat=True).distinct())
			if not isNone(cexecutor):
				caseresult = caseresult.filter(executor = cexecutor)
				cmodule = cmodule.filter(pk__in = caseresult.values_list("testcase", flat=True).distinct())
			if not isNone(cstart_date) or not isNone(cend_date):
				if not isNone(cstart_date):
					caseresult = caseresult.filter(exec_date__gte = cstart_date)
				if not isNone(cend_date):
					caseresult = caseresult.filter(exec_date__lte = cend_date)
				cdate = set(cmodule.values_list("id",flat = True))&(set(caseresult.values_list("testcase", flat=True)))
				cmodule = cmodule.filter(pk__in = cdate)
	else:
		subset2 = list(category.objects.filter(parent_id = pid).values_list("id",flat=True))
		subset3 = list(category.objects.filter(parent_id__in = subset2))
		subset = list(set(subset2).union(set(subset3)))		
		subset.append(pid)
		cmodule = testcase.objects.filter(category__in = subset)
		testmodule = casemodule.objects.filter(pk__in = cmodule.values_list("module", flat = True))
		caseresult = result.objects.filter(testcase__in = cmodule)
	listid = caseresult.values_list("testcase", flat=True).distinct()
	newresult = []
	for c in listid:
		p = caseresult.filter(testcase = c).order_by("-exec_date")[0]
		newresult.append(p)
	for m in testmodule:
		case[m.m_name] = cmodule.filter(module = m.id)
	return render_to_response("case/case_list.html", {"case":case, "testmodule":testmodule, "result":newresult, "listid":listid,"categoryid":categoryid, "cauthor":cauthor, 
		                      "cpriority":cpriority, "statue":cstatue, "mold":cmold, "ckeyword":ckeyword, "ctestmodule":ctestmodule, "cexecutor":cexecutor, "cstart_date":cstart_date, 
		                      "cend_date":cend_date, "cate1":cate1, "cate2":cate2, "cate3":cate3})


def allcaselist(request):
	case = {}
	cmodule = testcase.objects.all()
	testmodule = casemodule.objects.filter(pk__in = cmodule.values_list("module", flat = True))
	caseresult = result.objects.filter(testcase__in = cmodule)
	listid = caseresult.values_list("testcase", flat=True).distinct()
	newresult = []
	for c in listid:
		p = caseresult.filter(testcase = c).order_by("-exec_date")[0]
		newresult.append(p)
	for m in testmodule:
		case[m.m_name] = cmodule.filter(module = m.id)
	print case
	return render_to_response("case/case_list.html", {"case":case, "testmodule":testmodule, "result":newresult, "listid":listid})


def categorysearch(request):
	clist = []
	#一级
	master = category.objects.filter(parent_id__isnull=True)
	#二级
	for m in master:
		categorydic = {}
		s = {}
		categorydic["master"]=m.name
		categorydic["masterid"] = m.id
		second = category.objects.filter(parent_id = m.id)
		slist = []
		ms = []
		for s in second:
			msdic = {}					
			msdic["second"] = s.name
			msdic["secondid"] = s.id			
			third = category.objects.filter(parent_id = s.id)			
			td = []
			for t in third:
				thirdic = {}			
				thirdic["third"]=t.name
				thirdic["thirdid"] = t.id
				td.append(thirdic)
			msdic["thirdlist"]=td
			ms.append(msdic)
		categorydic["slist"]=ms
		clist.append(categorydic)
	# print clist
	return HttpResponse(json.dumps(clist))

<<<<<<< HEAD
def exec_log(request,pid):
	clist={}
	record = []
	loglist = result.objects.filter(testcase_id = int(pid))
	execrecord = list(loglist.values_list("result", flat = True))
	clist["Pass"] = execrecord.count("Pass")
	record.append(clist);
	for item in loglist:
		recorddic = {}
		recorddic["date"] = str(item.exec_date)
		recorddic["executor"] = item.executor
		recorddic["result"] = item.result
		recorddic["remark"] = item.r_remark
		record.append(recorddic)
	return HttpResponse(json.dumps(record))
=======
def execute_case(request):
	resp = {}
	try:
		caseid = request.POST['caseid']
		cresult = request.POST['cresult']
		executor = request.session['realname']
		executorid = request.session['id']
		exec_date = datetime.datetime.now()
		cr = result(testcase_id=caseid, result=cresult, exec_date=exec_date, executor=executor, executorid=executorid, isactived=1)
		cr.save()
		exedetail = {}
		exedetail['exec_date'] = exec_date.strftime("%Y-%m-%d %H:%M:%S")
		exedetail['executor'] = executor 
		resp["success"] = True
		resp["exedetail"] = exedetail
	except Exception, e:
		resp["success"] = False
		resp["message"] = e
	finally:	
		resp = json.dumps(resp)

		return HttpResponse(resp)


def update_rank(request):
	resp = {}
	try:
		rank_dict = json.loads(request.POST['rankdict'])
		module_id = request.POST['mid']
		print rank_dict
		print module_id
		for key in rank_dict.keys():
			tc = testcase.objects.get(id=key)
			tc.rank = rank_dict[key]
			tc.module_id = module_id
			tc.save()
		resp["success"] = True
	except Exception,e:
		resp["success"] = False
		print e
		# resp["message"] = e
	finally:
		resp = json.dumps(resp)
		# print "resp==",resp

		return HttpResponse(resp)

>>>>>>> origin/case
