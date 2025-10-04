function startCountdown(page, redirectUrl = null) {
  let countdown = 5;
  const timer = document.getElementById("timer");
  const interval = setInterval(() => {
    countdown--;
    timer.textContent = countdown;
    if (countdown <= 0) {
      clearInterval(interval);
      if (redirectUrl) window.location.href = redirectUrl;
    }
  }, 1000);
}
