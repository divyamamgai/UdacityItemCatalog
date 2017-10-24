(function (w, d, $) {
    $(function () {
    });
    $(d)
        .on('click', '.message .fa-close', function () {
            $(this).parent().remove();
        });
})(window, document, jQuery);
