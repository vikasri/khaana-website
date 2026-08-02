/* The feedback form.

   The fields are ours; the inbox is Google's. The form posts straight to the
   Google Form's formResponse endpoint with Google's own entry.N field names,
   which is why the inputs carry those names in the markup. So responses land
   in the same spreadsheet an embedded form would fill, while the page keeps
   Khaana's typography instead of showing Google's purple header and a "Sign
   in to Google to save your progress" line above the questions.

   Two consequences worth knowing.

   First, the post is cross-origin and Google sends no CORS headers on that
   endpoint, so nothing can read the reply. That is why the form targets a
   hidden iframe rather than using fetch: the browser performs an ordinary
   form post, the reply lands somewhere invisible, and the page never
   navigates. We learn that the request completed, not that Google stored it.
   The thank-you is therefore honest about what it knows.

   Second, this works with JavaScript switched off. The action, the field
   names and the target are all in the HTML. What is lost without this file is
   the page context and the inline thank-you, not the message itself. */
(function () {
  'use strict';

  /* The Google Form's field ids. Read off the form itself; they change only
     if a question is deleted and recreated.

     `page` is empty because the form has no "Page" question yet. Until it
     gains one the URL is prepended to the message instead, which keeps the
     context without needing the form changed. Fill this in and it moves to
     its own spreadsheet column. */
  var ENTRY = {
    message: 'entry.1093729377',
    page: ''
  };

  var form = document.getElementById('feedback-form');
  if (!form) return;

  var status = document.getElementById('ff-status');
  var button = form.querySelector('.ff-submit');
  var sink = document.getElementById('ff-sink');
  var trap = document.getElementById('ff-website');
  var message = document.getElementById('ff-message');
  var sent = false;

  /* Which page the feedback is about.

     Rebuilt against our own origin rather than used as given: this value ends
     up in a response we read as though it were ours, and a link posted
     anywhere could otherwise put arbitrary text, or a URL on somebody else's
     domain, into it. Anything that is not a plain path off this site falls
     back to the referrer, and failing that to nothing. */
  function sourcePage() {
    var from = new URLSearchParams(location.search).get('from') || '';
    if (from && /^\/[A-Za-z0-9._/-]*$/.test(from) && from.indexOf('//') === -1) {
      return location.origin + from;
    }
    if (document.referrer && document.referrer.indexOf(location.origin) === 0) {
      return document.referrer;
    }
    return '';
  }

  function say(text, ok) {
    status.textContent = text;
    status.className = 'ff-status' + (ok ? ' is-ok' : ' is-bad');
  }

  form.addEventListener('submit', function (ev) {
    // Silently drop anything that filled the honeypot. Telling a bot why
    // would only help it try again.
    if (trap && trap.value) {
      ev.preventDefault();
      say('Thank you. If it needs a reply, you will get one.', true);
      form.reset();
      return;
    }

    var page = sourcePage();
    if (page) {
      if (ENTRY.page) {
        var hidden = document.createElement('input');
        hidden.type = 'hidden';
        hidden.name = ENTRY.page;
        hidden.value = page;
        form.appendChild(hidden);
      } else {
        // No dedicated question yet, so the URL rides along at the top of the
        // message. Set here rather than earlier so the visitor never sees it
        // appear in the box they are typing in.
        message.value = 'Page: ' + page + '\n\n' + message.value;
      }
    }

    sent = true;
    button.disabled = true;
    say('Sending...', true);
  });

  /* The iframe fires load once when it is created and again when the post
     comes back, so the flag is what separates the two. Cross-origin means the
     reply cannot be inspected; reaching here means the request completed. */
  sink.addEventListener('load', function () {
    if (!sent) return;
    sent = false;
    button.disabled = false;
    form.reset();
    say('Thank you. If it needs a reply, you will get one.', true);
  });
}());
