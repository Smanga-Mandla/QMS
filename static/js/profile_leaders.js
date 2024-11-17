document.addEventListener("DOMContentLoaded", function() {
    // Function to toggle dropdown visibility
    function toggleDropdown(dropdownId) {
        const dropdown = document.getElementById(dropdownId);
        dropdown.style.display = dropdown.style.display === 'none' ? 'block' : 'none';
    }

    // Update date and time function
    function updateDateTime() {
        const now = new Date();
        const date = now.toLocaleDateString();
        const time = now.toLocaleTimeString();
        document.getElementById('access-time').value = `${date}, ${time}`;
    }

    // Initial call to update date and time
    updateDateTime();

    // Set interval to update date and time every second
    setInterval(updateDateTime, 1000);

    // Profile options button click event
    const profileOptionsBtn = document.getElementById('profile-options-btn');
    const profileOptions = document.getElementById('profile-options');

    profileOptionsBtn.addEventListener('click', () => {
        profileOptions.style.display = profileOptions.style.display === 'none' ? 'block' : 'none';
    });

    // File input change event for profile picture upload
    const fileInput = document.getElementById('file-input');
    const profilePic = document.getElementById('profile-pic');
    const initials = document.querySelector('.initials');

    fileInput.addEventListener('change', (event) => {
        const file = event.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                profilePic.src = e.target.result;
                initials.style.display = 'none';
            };
            reader.readAsDataURL(file);
        }
    });

    // Profile options click events
    const viewProfileBtn = document.getElementById('view-profile');
    const uploadPicBtn = document.getElementById('upload-pic');
    const deleteProfileBtn = document.getElementById('delete-profile');

    viewProfileBtn.addEventListener('click', () => {
        alert('Viewing Profile...'); // Example action, replace with actual functionality
    });

    uploadPicBtn.addEventListener('click', () => {
        fileInput.click();
    });

    deleteProfileBtn.addEventListener('click', () => {
        if (confirm('Are you sure you want to delete your profile?')) {
            alert('Profile Deleted'); // Example action, replace with actual functionality
            // Add functionality to delete profile
        }
    });

    // Close dropdowns when clicking outside
    document.addEventListener('click', function(event) {
        const profileDropdown = document.getElementById('profile-dropdown');
        const notificationsDropdown = document.getElementById('notifications-dropdown');

        if (!event.target.closest('.profile')) {
            profileDropdown.style.display = 'none';
        }

        if (!event.target.closest('.notifications')) {
            notificationsDropdown.style.display = 'none';
        }
    });
});
