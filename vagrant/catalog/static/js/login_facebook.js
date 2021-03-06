(function (w, d, $) {
    var $loginButton,
        $loginLoader,
        login_state = w.login_state;

    // Initialize Facebook SDK
    w.fbAsyncInit = function () {
        FB.init({
            appId: '1680669308673886',
            cookie: true,
            xfbml: true,
            version: 'v2.8'
        });
    };

    // Load Facebook SDK
    (function (d, s, id) {
        var js, fjs = d.getElementsByTagName(s)[0];
        if (d.getElementById(id)) return;
        js = d.createElement(s);
        js.id = id;
        js.src = "//connect.facebook.net/en_US/sdk.js";
        fjs.parentNode.insertBefore(js, fjs);
    }(d, 'script', 'facebook-jssdk'));

    function facebookLogin() {
        var access_token = FB.getAuthResponse()['accessToken'];
        // Verify facebook login using the received access token.
        FB.api('/me', function (response) {
            $loginButton.css('display', 'none');
            $loginLoader.css('display', 'inline-block');
            // Perform Facebook Login on our server side.
            $.ajax({
                type: 'POST',
                url: '/login/facebook/' + login_state,
                processData: false,
                data: access_token,
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
        });
    }

    // Expose facebookLogin function to global scope.
    w.facebookLogin = facebookLogin;

    $(function () {
        $loginButton = $('.login-button', d);
        $loginLoader = $('#login-loader', d);
    });
})(window, document, jQuery);