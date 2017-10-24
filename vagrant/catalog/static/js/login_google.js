(function (w, d, $) {
    var $loginButton,
        $loginLoader,
        login_state = w.login_state;

    function googleLogin(authResult) {
        if (authResult['code']) {
            $loginButton.hide();
            $loginLoader.show();
            $.ajax({
                type: 'POST',
                url: '/login/google/' + login_state,
                processData: false,
                data: authResult['code'],
                contentType: 'application/octet-stream; charset=utf-8',
                success: function (result) {

                }
            });
        }
    }

    w.googleLogin = googleLogin;

    $(function () {
        $loginButton = $('.log-button', d);
        $loginLoader = $('#login-loader', d);
    });
})(window, document, jQuery);