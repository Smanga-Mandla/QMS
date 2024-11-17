 document.addEventListener("DOMContentLoaded", function() {
    function updateDateTime() {
        const now = new Date();
        const date = now.toLocaleDateString();
        const time = now.toLocaleTimeString();
        document.getElementById('access-time').value = `${date}, ${time}`;
    }

    updateDateTime();
    setInterval(updateDateTime, 1000);

    const fileInput = document.getElementById('file-input');

    const profileOptionsBtn = document.getElementById('profile-options-btn');
    const profileOptions = document.getElementById('profile-options');
    const viewProfileBtn = document.getElementById('view-profile');
    const uploadPicBtn = document.getElementById('upload-pic');
    const deleteProfileBtn = document.getElementById('delete-profile');

    profileOptionsBtn.addEventListener('click', () => {
        profileOptions.style.display = profileOptions.style.display === 'none' ? 'block' : 'none';
    });

    viewProfileBtn.addEventListener('click', () => {
        alert('Viewing Profile...');
    });

    uploadPicBtn.addEventListener('click', () => {
        fileInput.click();
    });

    deleteProfileBtn.addEventListener('click', () => {
        if (confirm('Are you sure you want to delete your profile?')) {
            alert('Profile Deleted');
            // Add functionality to delete profile
        }
    });

    fileInput.addEventListener('change', (event) => {
        const file = event.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                const profilePic = document.getElementById('profile-pic');
                profilePic.src = e.target.result;
                document.querySelector('.initials').style.display = 'none';
            };
            reader.readAsDataURL(file);
        }
    });
});
