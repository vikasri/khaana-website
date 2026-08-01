document.addEventListener('DOMContentLoaded', function () {
  var toggle = document.querySelector('.nav-toggle');
  var links = document.querySelector('.nav-links');
  if (toggle && links) {
    toggle.addEventListener('click', function () {
      links.classList.toggle('open');
    });
  }
});


/* The sticky header wraps to two or three lines depending on width, so anything
   that needs to sit directly below it cannot hard-code an offset. Publish the
   measured height and let CSS use it. */
(function () {
  var header = document.querySelector('.site-header');
  if (!header) return;
  function publish() {
    document.documentElement.style.setProperty(
      '--header-h', Math.round(header.getBoundingClientRect().height) + 'px');
  }
  publish();
  window.addEventListener('resize', publish);
  window.addEventListener('load', publish);
})();
