/**
 * Created by abhi on 3/30/16.
 */

function signInCallback(authResult){
    if(authResult['code']){

        // Need to hide the signInButton since the user is logged in.
        $('#signInButton').attr('style', 'display: None');

        $.ajax({
            type: 'POST',
            url: '/gconnect?state={{ csrf_token }}',
            processData: false,
            contentType: 'application/octet-stream; charset=utf-8',
            data:authResult['code'],
            success: function (result) {
                if(result){
                    $('#result').html('Login successful! <br />' + result + '<br /> Redirecting...');
                setTimeout(function(){
                   window.location.href = "/";
                });
                } else if(authResult['error']){
                    console.log('There was an error: ' + authResult['error']);

                } else {
                    $('#result').html('Failed to make server call. Check' +
                        ' your configuration and console.')
                }
            }

        })
    }
}