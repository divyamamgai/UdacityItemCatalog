(function (w, d, $) {
    var $loginButton,
        $loginLoader,
        login_state = w.login_state;

    function googleLogin(authResult) {
        if (authResult['code']) {
            $loginButton.css('display', 'none');
            $loginLoader.css('display', 'inline-block');
            $.ajax({
                type: 'POST',
                url: '/login/google/' + login_state,
                processData: false,
                data: authResult['code'],
                contentType: 'application/octet-stream; charset=utf-8',
                success: function (result, status) {
                    if (status === 'success') {
                        w.location.href = '/catalog';
                    } else {
                        alert('Error occurred in the login process.\nMessage: ' + result);
                        $loginButton.css('display', 'block');
                        $loginLoader.css('display', 'none');
                    }
                }
            });
        }
    }

    w.googleLogin = googleLogin;

    $(function () {
        $loginButton = $('.login-button', d);
        $loginLoader = $('#login-loader', d);
    });
})(window, document, jQuery);