$(function() {

    $(".js-upload-photos").click(function() {
        $("#fileupload").click();
    });

    $("#fileupload").fileupload({
        dataType: 'json',
        sequentialUploads: true,

        start: function(e) {
            $("#modal-progress").modal("show");
        },

        stop: function(e) {
            $("#modal-progress").modal("hide");
        },

        progressall: function(e, data) {
            var progress = parseInt(data.loaded / data.total * 100, 10);
            var strProgress = progress + "%";
            $(".progress-bar").css({ "width": strProgress });
            $(".progress-bar").text(strProgress);
        },

        done: function(e, data) {
            if (data.result.is_valid) {
                var newRow = $(
                    '<tr>' +
                    '<td>' + data.result.name + '</td>' +
                    '</tr>'
                );
                if (data.result.type = "dcm") {
                    $("#gallery tbody").append(
                        newRow
                    );
                }
                if (data.result.type = "nii") {
                    $("#gallery_nii tbody").append(
                        newRow
                    );
                }
                if (data.result.type = "vtk") {
                    $("#gallery_vtk tbody").append(
                        newRow
                    );
                }
            }
        },
    });
});