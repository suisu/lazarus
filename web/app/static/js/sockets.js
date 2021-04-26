$(function() {
    $(".alert").not(".static").fadeTo(2000, 500).slideUp(1000, function(){
        $(".alert").slideUp(1000);
    });

    $.each($('#navbar').find('li'), function() {
        $(this).toggleClass('active', 
            window.location.pathname.indexOf($(this).find('a').attr('href')) > -1);
    }); 
    

    const socket = SocketSingleton.getInstance();
    $.each(['scan','github'], function(index, value) {
        updateProgressStatus(value, null);
    });

    /* vulnerability scan - listener */
    socket.on('scan_results', function(results) {
        // logger
        var flash = new Flash(results);
        flash.show();

        LocalStorager.setWithExpiry('scan', results.percentage, 420000);
        updateProgressStatus('scan', socket);
    });

    $('#scanbtnstop').on('click', function() {
        LocalStorager.setWithExpiry('scan', '0', 420000);
        updateProgressStatus('scan', socket);
        socket.emit('scan','stop');
    })

    /* vulnerability scan - sender */
    $('#scanbtn').on('click', function() {
        LocalStorager.setWithExpiry('scan', '0', 420000);
        socket.connect('http://localhost:5000');
        updateProgressStatus('scan', socket);
        socket.emit('scan','start');
    });

    /* github scan - listener */
    socket.on('github_results', function(results) {
        // logger
        var flash = new Flash(results);
        flash.show();

        LocalStorager.setWithExpiry('github', results.percentage, 420000);
        updateProgressStatus('github', socket);
    });

    /* github scan - sender */
    $('#githubbtn').on('click', function() {
        LocalStorager.setWithExpiry('github', '0', 420000);
        socket.connect('http://localhost:5000');
        updateProgressStatus('github', socket);
        socket.emit('github','start');
    });

    $('#githubbtnstop').on('click', function() {
        LocalStorager.setWithExpiry('github', '0', 420000);
        socket.emit('github','stop');
        updateProgressStatus('github', socket);
    })
});

  /* globals */
var SocketSingleton = (function () {
    var instance;

    function createInstance() {
        var object = io();
        return object;
    }

    return {
        getInstance: function() {
            if (!instance) {
                instance = createInstance();
                console.log('created instance of socket');
            }
            return instance;
        }    
    };
})();

class Flash {
    constructor(message) {
        this.category = message.alert;
        this.text = message.message;
    }
    show() {
        $('#bsalert').html(`<div class="alert alert-${this.category} alert-dismissable" role="alert">
            <button type="button" class="close" data-dismiss="alert" aria-label="close">
            <span aria-hidden="true">&times;</span></button>
            ${this.text}</div>`);
            $(".alert").show();
            $(".alert").fadeTo(2000, 500).slideUp(1000, function () {
                $(".alert").slideUp(1000);
        });
    }
}

window.onbeforeunload = function() {
    socket.emit('client disconnected');
}

class LocalStorager {
    static setWithExpiry(key, value, ttl) {
        console.log(`setting expiry on ${key}, ${value}, ${ttl}`)
        const now = new Date()
        const item = {
            value: value,
            expiry: now.getTime() + ttl,
        }
        localStorage.setItem(key, JSON.stringify(item))
    }
    static getWithExpiry(key) {
        const itemStr = localStorage.getItem(key)
        // if doesn't exist, return null
        if (!itemStr) {
            return null
        }

        const item = JSON.parse(itemStr)
        const now = new Date()
        if (now.getTime() > item.expiry) {
            localStorage.removeItem(key)
            return null
        }
        return item.value
    }
}

function updateProgressStatus(elem, socket) {
    let percentage = LocalStorager.getWithExpiry(elem);
    if (percentage) {
        $(`#progress-bar-${elem}`).css('width', `${percentage}%`);
        $(`#progress-bar-label-${elem}`).text(`${percentage}%`);
        $(`#${elem}btn`).prop('disabled', true);
        if (socket) socket.emit('client disconnected');
    }
}