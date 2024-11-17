function openMenu() {
    const menu = document.getElementById('menu');
    if (menu.style.display === 'block') {
        menu.style.display = 'none';
    } else {
        menu.style.display = 'block';
    }
}



/* Set the width of the sidebar to 250px and the left margin of the page content to 250px */
function openNav() {
    document.getElementById("mySidebar").style.width = "250px";
    document.getElementById("main").style.marginLeft = "250px";
}

/* Set the width of the sidebar to 0 and the left margin of the page content to 0 */
function closeNav() {
    document.getElementById("mySidebar").style.width = "0";
    document.getElementById("main").style.marginLeft = "0";
}

document.addEventListener('DOMContentLoaded', function() {
    // Timeline events (commented out for now, uncomment if needed)
    /*
    const eventsContainer = document.getElementById('events');
    const eventData = JSON.parse(localStorage.getItem('eventData'));

    if (eventData) {
        const eventItem = document.createElement('div');
        eventItem.classList.add('timeline-item');

        const eventDate = new Date().toLocaleDateString();
        eventItem.innerHTML = `
            <div class="date">${eventDate}</div>
            <div class="details">
                <span class="event">${eventData.title}</span>
                <span class="close-date">Close Date: ${eventData.closeDate}</span>
                <a href="${eventData.fileContent}" download="${eventData.fileName}">
                    <button class="action-btn">Download Attached File</button>
                </a>
                <a href="lecture2.html"><button class="add-submission-btn">Add Submission</button></a>
            </div>
        `;

        eventsContainer.appendChild(eventItem);
    }
    */

    // Calendar generation
    const daysElement = document.getElementById('days');
    const dateElement = document.getElementById('date');
    const prevButton = document.getElementById('prev');
    const nextButton = document.getElementById('next');

    let currentMonth = new Date().getMonth();
    let currentYear = new Date().getFullYear();

    function renderCalendar(month, year) {
        daysElement.innerHTML = '';
        const firstDay = new Date(year, month, 1).getDay();
        const lastDate = new Date(year, month + 1, 0).getDate();

        // Display the current month and year
        dateElement.textContent = new Date(year, month).toLocaleDateString('en-US', { month: 'long', year: 'numeric' });

        // Fill in the days
        for (let i = 0; i < firstDay; i++) {
            const emptyCell = document.createElement('div');
            daysElement.appendChild(emptyCell);
        }
        for (let i = 1; i <= lastDate; i++) {
            const dayCell = document.createElement('div');
            dayCell.textContent = i;
            daysElement.appendChild(dayCell);

            // Highlight the current day
            const currentDate = new Date();
            if (currentDate.getFullYear() === year && currentDate.getMonth() === month && currentDate.getDate() === i) {
                dayCell.classList.add('current-day');
            }
        }
    }

    prevButton.addEventListener('click', function() {
        currentMonth = (currentMonth - 1 + 12) % 12;
        if (currentMonth === 11) {
            currentYear--;
        }
        renderCalendar(currentMonth, currentYear);
    });

    nextButton.addEventListener('click', function() {
        currentMonth = (currentMonth + 1) % 12;
        if (currentMonth === 0) {
            currentYear++;
        }
        renderCalendar(currentMonth, currentYear);
    });

    renderCalendar(currentMonth, currentYear);

    // Mock data for submissions (replace with actual dynamic data)
    const submissions = [
        { email: 'example1@example.com', document: 'Document 1' },
        { email: 'example2@example.com', document: 'Document 2' },
        { email: 'example3@example.com', document: 'Document 3' }
    ];

    const submissionsDropdown = document.getElementById('submissions-dropdown');
    submissions.forEach(submission => {
        const submissionItem = document.createElement('div');
        submissionItem.textContent = `${submission.document} - ${submission.email}`;
        submissionItem.classList.add('submission-item');
        submissionsDropdown.appendChild(submissionItem);
    });
});

function toggleDropdown(dropdownId) {
    const dropdown = document.getElementById(dropdownId);
    if (dropdown.style.display === 'block') {
        dropdown.style.display = 'none';
    } else {
        // Hide all dropdowns first
        document.querySelectorAll('.dropdown, .notifications-dropdown').forEach(d => d.style.display = 'none');
        // Show the targeted dropdown
        dropdown.style.display = 'block';
    }
}
