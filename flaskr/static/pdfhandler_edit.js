function orderedSelect(buttonObject) {
    // -- GET THE FILENAME + PAGE NUMBER

    var id = buttonObject.id;
    // const re = '/(-)\d$/'
    // const split = id.split(re);
    // const fileName = split[0];
    // const pageNumber = split[1];
    
    // -- CREATE ARRAY (IF THERE IS NOT ALREADY AN ARRAY)

    if (typeof globalThis.selectedFiles === "undefined") { //|| (!(globalThis.selectedFiles.isArray))) {
        globalThis.selectedFiles = [];
        console.log(globalThis.selectedFiles.isArray)
    }

    console.log(globalThis.selectedFiles);

    // -- ADD/SUBTRACT TO GLOBAL ARRAY
    var index = globalThis.selectedFiles.indexOf(id);

    if (index === -1) { // Push to array
        globalThis.selectedFiles.push(id);
        buttonObject.innerHTML = globalThis.selectedFiles.length;
    } else { // Remove from array
        globalThis.selectedFiles.splice(index, 1)
        buttonObject.innerHTML = "Select";
    }

    console.log(globalThis.selectedFiles);

    // -- CHANGE THE CLASSES OF THE OBJECT
    buttonObject.classList.toggle('btn-outline-dark');
    buttonObject.classList.toggle('btn-primary');
}

function sendPostRequest(url){
    // XXX: need to handle when selectedFiles is empty
    var xhr = new XMLHttpRequest();
    xhr.open("POST", url, true); // NOTE: async is set to true
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.send(JSON.stringify(globalThis.selectedFiles));
}