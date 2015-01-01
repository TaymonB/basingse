$(function() {

  window.onscriptsload = function() {

    var current_interval_id = null;

    var csrftoken = $.cookie('csrftoken');
    $.ajaxSetup({
      beforeSend: function(xhr, settings) {
        if (!/^(GET|HEAD|OPTIONS|TRACE)$/.test(settings.type) && !this.crossDomain) {
          xhr.setRequestHeader("X-CSRFToken", csrftoken);
        }
      }
    });

    $(document).ajaxError(function(event, jqxhr, settings, thrown_error) {
      var error_alert = $('\
        <div class="alert alert-danger alert-dismissible" role="alert">\
          <button type="button" class="close" data-dismiss="alert" aria-label="Close">\
            <span aria-hidden="true">&times;</span>\
          </button>\
        </div>\
      ');
      var error_msg = undefined;
      try {
        error_msg = $.parseJSON(jqXHR.responseText).message;
      } catch (e) {}
      if (typeof error_msg === 'undefined') {
        error_alert.append($('<strong>Unspecified error communicating with server.</strong>'));
      } else {
        error_alert.append(
          $('<strong>Error communicating with server:</strong> '),
          document.createTextNode(error_msg));
      }
      $('#status-msg').before(error_alert);
    });

    var set_disconnected_mode = function() {
      window.clearInterval(current_interval_id);
      $('#status-msg').hide();
      $('#noVNC-canvas').hide();
      $('#off-buttons').show();
      $('#on-buttons').hide();
    };

    var set_connected_mode = function() {
      window.clearInterval(current_interval_id);
      current_interval_id = window.setInterval(function() {
        $.post('heartbeat');
      }, 60000);
      $('#status-msg').hide();
      $('#noVNC-canvas').show();
      $('#off-buttons').hide();
      $('#on-buttons').show();
    };

    var set_busy_mode = function(ok, status_msg) {
      window.clearInterval(current_interval_id);
      var class_to_remove, class_to_add;
      if (ok) {
        class_to_remove = 'alert-warning alert-danger';
        class_to_add = 'alert-info';
      } else {
        class_to_remove = 'alert-info alert-danger';
        class_to_add = 'alert-warning';
      }
      $('#status-msg').removeClass(class_to_remove).addClass(class_to_add).text(status_msg).show();
      $('#noVNC-canvas').hide();
      $('#off-buttons').hide();
      $('#on-buttons').hide();
    };

    var set_broken_mode = function(status_msg) {
      window.clearInterval(current_interval_id);
      $('#status-msg').removeClass('alert-info alert-warning').addClass(alert-danger).text(status_msg +
                                                                                           ' Please refresh and try again.').show();
      $('#noVNC-canvas').hide();
      $('#off-buttons').hide();
      $('#on-buttons').hide();
    };

    var rfb = new RFB({
      target: $('#noVNC-canvas')[0],
      local_cursor: true,
      onUpdateState: function(rfb, state, oldstate, status_msg) {
        switch (state) {
        case 'normal':
          set_connected_mode();
          break;
        case 'loaded':
        case 'disconnected':
          set_disconnected_mode();
          break;
        case 'failed':
          if (oldstate === 'normal') {
            set_busy_mode(false, status_msg);
          } else {
            set_broken_mode(status_msg);
          }
          break;
        case 'fatal':
          set_broken_mode(status_msg);
          break;
        default:
          set_busy_mode(true, status_msg);
        }
      }
    });

    var currently_imaging = false;
    var ready_to_start = false;

    var set_mode_for_status = function(status) {
      if (rfb._rfb_state === 'loaded' || rfb._rfb_state === 'disconnected') {
        switch (status.state) {
        case 'active':
          currently_imaging = false;
          set_busy_mode(true, 'Machine is online. Waiting to connect\u2026');
          rfb.connect(status.address, '5700', status.password);
          break;
        case 'stopped':
          if (currently_imaging) {
            $.post('start', set_mode_for_status);
          }
          currently_imaging = false;
          $('#status-msg').text('Waiting for machine to come online\u2026');
          break;
        case 'queued':
          currently_imaging = true;
          $('#status-msg').text('Machine\u2019s hard drive queued for imaging. This may take a while\u2026');
          break;
        case 'imaging':
          currently_imaging = true;
          $('#status-msg').text('Machine\u2019s hard drive is imaging. ' + status.percent + '% complete\u2026');
          break;
        default:
          set_broken_mode('Machine has problematic status: ' + status.state + '.');
        }
      }
    };

    var set_awaiting_address_mode = function() {
      window.clearInterval(current_interval_id);
      current_interval_id = window.setInterval(function() {
        $.getJSON('status', set_mode_for_status);
      }, 2000);
      $('#status-msg').removeClass('alert-warning alert-danger').addClass('alert-info').text('Waiting for machine status\u2026').show();
      $('#noVNC-canvas').hide();
      $('#off-buttons').hide();
      $('#on-buttons').hide();
    };

    $('#start').on('click', function() {
      $.post('start', set_mode_for_status);
      set_awaiting_address_mode();
    });

    $('#cad').on('click', function() {
      rfb.sendCtrlAltDel();
    });

    $('#shutdown').on('click', function() {
      $.post('shutdown');
    });

    $('#reset').on('click', function() {
      $.post('reset');
    });

    $('#power-off').on('click', function() {
      $.post('stop');
    });

    set_mode_for_status(InitialStatus);

  };

  INCLUDE_URI = 'static/uservm/novnc/';
  Util.load_scripts(['webutil.js', 'base64.js', 'websock.js', 'des.js',
                     'keysymdef.js', 'keyboard.js', 'input.js', 'display.js',
                     'jsunzip.js', 'rfb.js', 'keysym.js']);

});
