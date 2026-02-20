/**
 * AdSense ad unit initialisation.
 * Loaded dynamically by the cookie consent banner ONLY after user accepts.
 * Each page that includes ad units calls pushAd() on DOMContentLoaded.
 *
 * Replace ADSENSE_PUBLISHER_ID and slot IDs in app/config/adsense_config.js
 * once your AdSense account is approved.
 */

window.pushAd = function () {
  try {
    (window.adsbygoogle = window.adsbygoogle || []).push({});
  } catch (e) {
    // AdSense not yet loaded — consent not given or script blocked
  }
};
