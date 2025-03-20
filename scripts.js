// Include Navbar
document.getElementById('navbar-placeholder').innerHTML = `
  <nav class="navbar navbar-expand-lg navbar-light bg-light">
    <div class="container-fluid">
      <a class="navbar-brand" href="index.html">Home</a>
      <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav" aria-controls="navbarNav" aria-expanded="false" aria-label="Toggle navigation">
        <span class="navbar-toggler-icon"></span>
      </button>
      <div class="collapse navbar-collapse" id="navbarNav">
        <ul class="navbar-nav">
          <li class="nav-item"><a class="nav-link" href="this-week.html">This Week</a></li>
          <li class="nav-item"><a class="nav-link" href="full-calendar.html">Full Calendar</a></li>
          <li class="nav-item"><a class="nav-link" href="theaters.html">Theaters</a></li>
        </ul>
      </div>
    </div>
  </nav>
`;

// Get current week range
function getCurrentWeek() {
  const today = new Date();
  const startOfWeek = new Date(today.setDate(today.getDate() - today.getDay())); // Sunday
  const endOfWeek = new Date(today.setDate(today.getDate() - today.getDay() + 6)); // Saturday

  return { startOfWeek, endOfWeek };
}

// Check if a date is within the current week
function isDateThisWeek(date) {
  const { startOfWeek, endOfWeek } = getCurrentWeek();
  const parsedDate = new Date(date);

  return parsedDate >= startOfWeek && parsedDate <= endOfWeek;
}

// Parse the CSV and group by film
function loadShowtimes() {
  Papa.parse('updated_file.csv', {
    download: true,
    header: true,
    dynamicTyping: true,
    complete: function(results) {
      // Filter the data to only include showtimes for this week
      const thisWeekShowtimes = results.data.filter(row => isDateThisWeek(row.Date));
      
      // Group showtimes by film
      const films = {};
      
      thisWeekShowtimes.forEach(row => {
        if (!films[row.Film]) {
          films[row.Film] = [];
        }
        films[row.Film].push(row);
      });

      // Sort films by their earliest showtime
      const sortedFilms = Object.keys(films).sort((a, b) => {
        const earliestA = films[a].reduce((earliest, row) => {
          const showtimeDate = new Date(row.Date + ' ' + row.Time);
          return (earliest === null || showtimeDate < earliest) ? showtimeDate : earliest;
        }, null);

        const earliestB = films[b].reduce((earliest, row) => {
          const showtimeDate = new Date(row.Date + ' ' + row.Time);
          return (earliest === null || showtimeDate < earliest) ? showtimeDate : earliest;
        }, null);

        return earliestA - earliestB;
      });

      const filmsList = document.getElementById('films-list');

      // Iterate over the films and display them
      sortedFilms.forEach(filmName => {
        const filmShowtimes = films[filmName];
        const filmRuntime = filmShowtimes[0].Runtime;  // Assuming the runtime is the same for all showtimes of a film

        const filmItem = document.createElement('div');
        filmItem.classList.add('film-item');
        filmItem.innerHTML = `
          <h4>${filmName} - <span class="text-muted">Runtime: ${filmRuntime}</span></h4>
          <h5>Showtimes</h5>
          <ul class="list-group">
            ${filmShowtimes.sort((a, b) => new Date(a.Date + ' ' + a.Time) - new Date(b.Date + ' ' + b.Time))
              .map(row => {
                const isAlmostSoldOut = row.isAlmostSoldOut === 'TRUE';
                return `
                  <li class="list-group-item showtime-item ${isAlmostSoldOut ? 'almost-sold-out' : ''}">
                    <span class="showtime-details">
                      <strong>Theater:</strong> ${row.Theater} | 
                      <strong>Showtime:</strong> ${row.Time} on ${row.Date}
                    </span>
                  </li>
                `;
              }).join('')}
          </ul>
        `;

        filmsList.appendChild(filmItem);
      });
    }
  });
}

// Load the showtimes when the page is loaded
window.onload = loadShowtimes;
