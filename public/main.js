let deviceId = null
let isGathering = false
let isTraining = false

async function changeRoom(room) {
  const data = {name: room, deviceId: deviceId};
  await fetch('/api/room', {
    method: 'POST',
    headers: {'Accept': 'application/json', 'Content-Type': 'application/json'},
    body: JSON.stringify(data)
  })
}

async function startGathering() {
  const el =
      document.querySelector('input[type=radio][name=gatheringMode]:checked')
  const action = el.value
  const data = {action, deviceId: deviceId};
  await fetch('/api/gathering', {
    method: 'POST',
    headers: {'Accept': 'application/json', 'Content-Type': 'application/json'},
    body: JSON.stringify(data)
  })
}

async function stopGathering() {
  const data = {action: 'stop', deviceId: deviceId};
  await fetch('/api/gathering', {
    method: 'POST',
    headers: {'Accept': 'application/json', 'Content-Type': 'application/json'},
    body: JSON.stringify(data)
  })
}

async function startTraining() {
  const data = {deviceId: deviceId};
  await fetch('/api/training', {
    method: 'POST',
    headers: {'Accept': 'application/json', 'Content-Type': 'application/json'},
    body: JSON.stringify(data)
  })
}

async function stopTraining() {
  await fetch('/api/training', {
    method: 'DELETE',
    headers: {'Accept': 'application/json', 'Content-Type': 'application/json'}
  })
}

function empty(element) {
  while (element.firstElementChild) {
    element.firstElementChild.remove();
  }
}

async function getEntities() {
  const res = await fetch('/api/entities', {
    method: 'GET',
  })
  const data = await res.json()
  console.log(data)
  populateEntities(data)
}

function createDeviceHTMLEntry(device) {
  const li = document.createElement('li')
  const button = document.createElement('button')
  button.innerText = device.name
  li.appendChild(button)
  button.addEventListener('click', () => setEntity(device.id));
  return li
}

function populateEntities(data) {
  const devicesListE = document.querySelector('#devicesList')
  empty(devicesListE)
  const fragment = new DocumentFragment()
  const devices = data.filter(x => x.measuredValues);
  for (const device of devices) {
    fragment.appendChild(createDeviceHTMLEntry(device))
  }
  devicesListE.appendChild(fragment)
}

function setEntity(_deviceId) {
  deviceId = _deviceId
  console.log(`device id set to: ${deviceId}`)
}

async function toggleGathering(el) {
  el.disabled = true
  if (isGathering) {
    await stopGathering();
  }
  else {
    await startGathering();
  }
  isGathering = !isGathering
  el.innerText = isGathering ? 'Stop Gathering' : 'Start Gathering'
  el.disabled = false
}

async function toggleTraining(el) {
  el.disabled = true;
  if (isGathering) {
    await stopTraining();
  } else {
    await startTraining();
  }
  isTraining = !isTraining
  el.innerText = isTraining ? 'Stop Training' : 'Start Training'
  el.disabled = false
}

function msgRoomHandler(msg) {
  if (msg.deviceId !== deviceId) return;
  const el = document.getElementById('room')
  el.innerText = msg.room
}

function main() {}

addEventListener('DOMContentLoaded', main);

const exampleSocket = new WebSocket('ws://localhost:8000/ws');

exampleSocket.onopen = (event) => {
  const msg = {type: 'ping'};

  exampleSocket.send(JSON.stringify(msg));
};

exampleSocket.onmessage = (event) => {
  const msg = JSON.parse(event.data)
  switch (msg.type) {
    case 'pong':
      console.log('pong')
      break;
    case 'room':
      msgRoomHandler(msg)
      break;
  }
};