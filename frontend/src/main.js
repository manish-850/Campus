import './style.css'
import axios from 'axios';




async function submitComplaint() {
    const name = document.getElementById('name').value;
    const registrationNo = document.getElementById('regNo').value;
    const block = document.getElementById('block').value;
    const roomNo = document.getElementById('room').value;
    const des = document.getElementById('des').value;
    console.log(name, registrationNo, block, roomNo, des);
//   try {
//     const response = await fetch('http://localhost:8000/complaints');
//     const data = await response.json();
//     console.log(data);
//   } catch (error) {
//     console.error('Error fetching data:', error);
//   }
}
const button = document.getElementById('fetchButton');
button.addEventListener('click', fetchData);