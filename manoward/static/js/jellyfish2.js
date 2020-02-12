/* Jellyfish2 Share JavaScript Functions

Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

*/

window.console.log("Jellyfish2 Main JS File Loaded")

function display_table(table_id, data_list, column_list_dict){
	
	$(document).ready(function() {
		$(table_id).DataTable( {
			data: data_list , 
			columns: column_list_dict
		} );
	} );	

}

function acoll_handler( item, extrastring, table_id ){
	window.console.log("In Audit")
	endpoint = item + extrastring
	$.getJSON(endpoint, function(data){
		window.console.log("Request Made")
		table_data = data.results
		window.console.log(table_data)
		
		table_data_array = new Array()
		
		// Change My Data for DataTable
		for (row in table_data) {
			item0 = "<a href='/display/audit/" + String(table_data[row]["acoll_id"]) + "'> " + table_data[row]["acoll_text"].toLowerCase() + " </a> "
			// Hiding Acoll_ID
			//item1 = table_data[row]["acoll_id"]
			item2 = table_data[row]["acoll_passed"]
			item3 = table_data[row]["acoll_failed"]
			item4 = table_data[row]["acoll_exempt"]
			item5 = new Date(table_data[row]["acoll_initial_audit"]*1000)
			item6 = new Date(table_data[row]["acoll_last_audit"]*1000)
			table_data_array.push([item0, /* item1, */ item2, item3, item4, item5, item6])
		}
		
		columns_headers = [
						{ title: "Audit" },
						/* { title: "ID" }, */
						{ title: "Passed" },
						{ title: "Failed" },
						{ title: "Exempt" },
						{ title: "First Audit Date" },
						{ title: "Latest Audit Date" }
					]
					
		display_table(table_id, table_data_array, columns_headers)
		
		window.console.log(table_data_array)
 
		
	})
}

function apop_handler( item, extrastring, table_id ){
	window.console.log("In POP")
	endpoint = item + extrastring
	$.getJSON(endpoint, function(data){
		window.console.log("Request Made")
		table_data = data.results
		window.console.log(table_data)
		
		table_data_array = new Array()
		
		// Change My Data for DataTable
		for (row in table_data) {
			// Link to Audit Data
			item0 = "<a href=/display/audit/" + String(table_data[row]["fk_audits_id"]) + ">Audit No: " + String(table_data[row]["fk_audits_id"]) + "</a>"
			// Not Displaying POP ID
			//item1 = table_data[row]["pop_id"]
			item2 = table_data[row]["pop_text"]
			item3 = table_data[row]["pop_failed"]
			item4 = table_data[row]["pop_passed"]
			item5 = table_data[row]["pop_exempt"]
			item6 = new Date(table_data[row]["pop_initial_audit"]*1000)
			item7 = new Date(table_data[row]["pop_last_audit"]*1000)
			table_data_array.push([item0, /*item1,*/ item2, item3, item4, item5, item6, item7])
		}
		
		columns_headers = [
						{ title: "Audit Number" },
						/* title: "POP Number" }, */
						{ title: "POP" },
						{ title: "Passed" },
						{ title: "Failed" },
						{ title: "Exempt" },
						{ title: "First Audit Date" },
						{ title: "Latest Audit Date" }
					]
					
		display_table(table_id, table_data_array, columns_headers)
		
		window.console.log(table_data_array)
 
		
	})
}

function asrvtype_handler( item, extrastring, table_id ){
	window.console.log("In SRVTYPE")
	endpoint = item + extrastring
	$.getJSON(endpoint, function(data){
		window.console.log("Request Made")
		table_data = data.results
		window.console.log(table_data)
		
		table_data_array = new Array()
		
		// Change My Data for DataTable
		for (row in table_data) {
			// Link to Audit Data
			item0 = "<a href=/display/audit/" + String(table_data[row]["fk_audits_id"]) + ">Audit No: " + String(table_data[row]["fk_audits_id"]) + "</a>"
			// Not Displaying SRVTYPE ID
			//item1 = table_data[row]["srvtype_id"]
			item2 = table_data[row]["srvtype_text"]
			item3 = table_data[row]["srvtype_failed"]
			item4 = table_data[row]["srvtype_passed"]
			item5 = table_data[row]["srvtype_exempt"]
			item6 = new Date(table_data[row]["srvtype_initial_audit"]*1000)
			item7 = new Date(table_data[row]["srvtype_last_audit"]*1000)
			table_data_array.push([item0, /*item1,*/ item2, item3, item4, item5, item6, item7])
		}
		
		columns_headers = [
						{ title: "Audit Number" },
						/* title: "POP Number" }, */
						{ title: "SRVTYPE" },
						{ title: "Passed" },
						{ title: "Failed" },
						{ title: "Exempt" },
						{ title: "First Audit Date" },
						{ title: "Latest Audit Date" }
					]
					
		display_table(table_id, table_data_array, columns_headers)
		
		window.console.log(table_data_array)
 
		
	})
}

function toggleDiv(divId) {

   $("#"+divId).toggle();

}

/* Take Data from Data Tables And toss it into A Format Ready for Google Charts*/
function countitems(arraytocount, column, columnname){
	//console.log("Party")
	//console.log(arraytocount)
	var results = {}
	
	for (var i = 0; i < arraytocount.length; i++) {
		if ( arraytocount[i][column] in results ) {
			// The Most Needful of the Needed
			results[arraytocount[i][column]]++
		} else {
			// First Insert
			results[arraytocount[i][column]] = 1
		}
	}
	
	var resultsArray = [ [ columnname, "Amount" ] ]
	//console.log(results)

	
	for (var key in results) {
		//console.log(key)
		//console.log(results[key])
		resultsArray.push([ key, results[key] ])
	}
		
	//console.log(resultsArray)
	return resultsArray
	
}

function range_to_gdatatable( api_object, left_column, right_column){
	

	
	var parsed_data_table_array = [ [ left_column[0], right_column[0] ] ]

	for (var rowindex=0; rowindex < api_object["data"].length; rowindex++) {
		// Push Data into my Array	
		parsed_data_table_array.push( [ api_object["data"][rowindex]["attributes"][left_column[1]], api_object["data"][rowindex]["attributes"][right_column[1]] ] )
	}
	
	return parsed_data_table_array
	
}

function merge_arrays_for_gdatatable( array_of_arrays_of_array ){
	
	// First array is the primary item.
	columns = array_of_arrays_of_array.length;
	
	rows = array_of_arrays_of_array[0].length;
	
	header_array = [ array_of_arrays_of_array[0][0][0] ]
	

	final_array = []
	
	for (var headerItem=0; headerItem < columns; headerItem++){
		header_array.push(array_of_arrays_of_array[headerItem][0][1])
	}
	
	final_array.push(header_array)
	
	for (var rowindex=1; rowindex < rows; rowindex++) {
		this_row = []
		for (var columnindex=0; columnindex < columns; columnindex++){
			if ( columnindex == 0 ) {
				this_row.push(array_of_arrays_of_array[columnindex][rowindex][0])
			}
			
			this_row.push(array_of_arrays_of_array[columnindex][rowindex][1])
		}
		final_array.push(this_row)
	}
	
	return final_array
}
	
