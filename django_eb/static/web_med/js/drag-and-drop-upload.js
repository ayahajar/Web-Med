$(function() {
    $("#fileupload").fileupload({
        dataType: 'json',
        done: function(e, data) {
            if (data.result.is_valid) {
                var newRow = $(
                    '<tr>' +
                    '<td>' + data.result.name + '</td>' +
                    '</tr>'
                );
                $("#gallery tbody").append(
                    newRow
                )
            }
        }
    });
});