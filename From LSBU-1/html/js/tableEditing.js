function search(searchStr){
	var table = document.getElementById('tbody');
	var nextRow = table.firstElementChild;
	while (nextRow !== null){
		var match = false;
		for (var i=1; i < nextRow.children.length; i++){ 	//(no need to search enabled row (i=0))
			if (nextRow.children[i].innerHTML.search(searchStr) >= 0){
				//match found
				match = true;
				break;
			}
		}
		if (match == true){
			nextRow.style.display = 'table-row';
		}else{
			nextRow.style.display = 'none';
		}
		nextRow = nextRow.nextElementSibling;
	}
}

function countChannels(){
	var table = document.getElementById('tbody');
	var numEnabled = 0;
	var numDisabled = 0;
	var nextRow = table.firstElementChild;
	while (nextRow !== null){
		if (nextRow.firstElementChild.tag == "1"){
			numEnabled++;
		}else{
			numDisabled++;
		}
		nextRow = nextRow.nextElementSibling;
	}
	var total = numEnabled + numDisabled;
	document.getElementById('topLeftDiv').innerHTML = numEnabled + " of " + total + " channels enabled.";
}

function enabledEdit(){
	if (this.tag == "1"){
		//1 signifies enabled. - disable.
		this.firstElementChild.style.backgroundImage = "url('/images/disabled.png')"; 
		this.tag = "0";
	}else{
		this.firstElementChild.style.backgroundImage = "url('/images/enabled.png')"; 
		this.tag = "1";
	}
	//update text displaying number of channels enabled in table.
	countChannels();
}

function textEdit(){
	var textBox = document.getElementById('editText');
	textBox.currentCell = this;
	var rect = this.getBoundingClientRect();
	textBox.style.left = rect.left + 'px';
	textBox.style.top = rect.top + 'px';
	textBox.style.width = (rect.right - rect.left-4) + 'px';
	textBox.style.height = (rect.bottom - rect.top -4) + 'px';
  textBox.maxLength = this.maxLength;
	textBox.value = this.innerHTML;
	textBox.setSelectionRange(textBox.value.length, textBox.value.length);
	textBox.style.visibility = 'visible';
	textBox.focus();
}
function textEditHide(){
	//occurs on escape
	document.getElementById('editText').style.visibility = 'hidden';
}
function comboEdit(){
	var comboBox = document.getElementById('editCombo');
	comboBox.currentCell = this;
	var rect = this.getBoundingClientRect();
	comboBox.style.left = rect.left + 'px';
	comboBox.style.top = rect.top + 'px';
	comboBox.style.width = (rect.right - rect.left) + 'px';
	comboBox.style.height = (rect.bottom - rect.top) + 'px';
	comboBox.value = this.innerHTML;
	comboBox.style.visibility = 'visible';
	comboBox.focus();
}

function comboEditChange(){
	var combo= document.getElementById('editCombo');
	if (combo.doNotExecute == true){
		//signifies escape key pressed.
		combo.doNotExecute = false;
	}else{
		combo.currentCell.innerHTML = combo.value;
		combo.style.visibility = 'hidden';
	}
}

function textEditKeyDown(e) {
	var text = document.getElementById('editText');
	if (e.keyCode == 13) {
		//enter
		text.currentCell.innerHTML = text.value;
		text.style.visibility = 'hidden';
	}else if (e.keyCode == 9) {
		e.preventDefault();
		//tab
		text.currentCell.innerHTML = text.value;
		text.style.visibility = 'hidden';
		text.currentCell.nextElementSibling.click();
	}else if (e.keyCode == 27) {
		// ESCAPE
		text.doNotExecute = true;
		text.style.visibility = 'hidden';
	}
}
function comboEditKeyDown(e) {
	var combo = document.getElementById('editCombo');
	if (e.keyCode == 13) {
		//enter
		combo.currentCell.innerHTML = combo.value;
		combo.style.visibility = 'hidden';
	}else if (e.keyCode == 9) {
		e.preventDefault();
		//tab
		combo.currentCell.innerHTML = combo.value;
		combo.style.visibility = 'hidden';
		combo.currentCell.nextElementSibling.click();
	}else if (e.keyCode == 27) {
		// ESCAPE
		combo.style.visibility = 'hidden';
		combo.doNotExecute = true;
	}
}

function textEditDone(){
	var text = document.getElementById('editText');
	if (text.doNotExecute == true){
		//signifies escape key pressed.
		text.doNotExecute = false;
	}else{
		text.currentCell.innerHTML = text.value;
    if (text.currentCell.index == 5){
      setAllIntervals(text.value);
    }
		text.style.visibility = 'hidden';
	}
}

function showLoader(){
	document.getElementById('loader-wrapper').style.visibility = 'visible';
}
function hideLoader(){
	document.getElementById('loader-wrapper').style.visibility = 'hidden';
}
