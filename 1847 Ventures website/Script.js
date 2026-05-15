// Smooth scroll to section
function scrollToSection(id) {
  const section = document.getElementById(id);
  if (section) {
    section.scrollIntoView({ behavior: 'smooth' });
  }
}

// Navbar background color change on scroll
window.addEventListener('scroll', function () {
  const navbar = document.getElementById('navbar');
  if (window.scrollY > 50) {
    navbar.classList.add('scrolled');
  } else {
    navbar.classList.remove('scrolled');
  }
});

// Modal logic
const modal = document.getElementById("subscribeModal");
const ctaButton = document.getElementById("cta-button");
const ctaHeroButton = document.getElementById("cta-button-hero");
const closeBtn = document.querySelector(".close");

ctaButton.addEventListener("click", () => modal.style.display = "block");
ctaHeroButton.addEventListener("click", () => modal.style.display = "block");
closeBtn.addEventListener("click", () => modal.style.display = "none");

window.addEventListener("click", (e) => {
  if (e.target === modal) modal.style.display = "none";
});

// Initialize intl-tel-input for phone field
const phoneInput = document.querySelector("#phone");
const iti = window.intlTelInput(phoneInput, {
  initialCountry: "auto",
  separateDialCode: true,
  geoIpLookup: function (callback) {
    fetch("https://ipapi.co/json")
      .then(res => res.json())
      .then(data => callback(data.country_code))
      .catch(() => callback("us"));
  },
  utilsScript: "https://cdnjs.cloudflare.com/ajax/libs/intl-tel-input/17.0.8/js/utils.js"
});

// Populate nationality dropdown with flags
const countries = window.intlTelInputGlobals.getCountryData();
const countrySelect = document.getElementById("countrySelect");

countries.forEach(country => {
  const option = document.createElement("option");
  option.value = country.iso2;
  option.textContent = country.name;
  option.style.backgroundImage = `url('https://flagcdn.com/24x18/${country.iso2}.png')`;
  countrySelect.appendChild(option);
});
 this.innerHTML = `
    <h3 style="text-align: center; color: forestgreen;">
      Thanks for contacting us, ${name.split(' ')[0] || 'friend'}!<br>
      We’ll be in touch shortly.
    </h3>
  `;

  // Auto-close the modal after 4 seconds
  setTimeout(() => {
    modal.style.display = "none";
    this.reset();
    location.reload(); // optional: reload to reset form HTML
  }, 4000);
});
