$(document).ready(function(){

	$(".flip").click(function(){
		$(".flip").toggleClass("drapdown");
		$(".panel").toggle();
		var panel = $(this).parent().parent().next(".panel");
		console.log(panel.length);
        content="这是一个内容很好<br/>这是一个内容很好<br/>这是一个内容很好<br/>这是一个内容很好<br/>"
		if(panel.length == 0){
			$(this).parent().parent().after("<tr class='row panel'><td><span>"+content+"<span></td></tr>");
		}

	});


});