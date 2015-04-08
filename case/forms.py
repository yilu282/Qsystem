# coding=utf-8
from django import forms

class searchForm(forms.Form):
	cate1 = forms.CharField(required=False)
	cate2 = forms.CharField(required=False)
	cate3 = forms.CharField(required=False)
	categoryid = forms.CharField(max_length=100, required=False)
	testmodule = forms.CharField(required=False)
	priority = forms.CharField(required=False)
	status = forms.CharField(required=False)
	mold = forms.CharField(required=False)
	author = forms.CharField(required=False)
	executor = forms.CharField(required=False)
	start_date = forms.DateField(required=False)
	end_date = forms.DateField(required=False)
	exec_status = forms.CharField(required=False)
	keyword = forms.CharField(required=False)
	
class add_procateForm(forms.Form):
	procate_title = forms.CharField(required=True,error_messages={'required': u'变更内容不能为空'})
	procate_id = forms.DateField(required=False)
	procate_level = forms.DateField(required=False)