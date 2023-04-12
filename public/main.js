class RESTClient extends EventTarget {
  constructor() {
    super();
    this.ws
  }

  async req({path, method, data}) {
    const {qs, body} = method.toLowerCase() === 'get' ?
        {qs: `?${new URLSearchParams(data).toString()}`} :
        {body: JSON.stringify(data)};
    const res = await fetch(path + (qs || ''), {
      method,
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      },
      body
    })

    return res.json()
  }

  async changeRoom(name, deviceId) {
    const data = {name, deviceId};
    return this.req({path: '/api/room', method: 'POST', data})
  }

  async startGathering(action, deviceId) {
    const data = {action, deviceId};
    return this.req({path: '/api/gathering', method: 'POST', data})
  }

  async stopGathering(deviceId) {
    const data = {action: 'stop', deviceId};
    return this.req({path: '/api/gathering', method: 'POST', data})
  }

  async startTraining(optimize, deviceId) {
    const data = {deviceId, optimize};
    return this.req({path: '/api/training', method: 'POST', data})
  }

  async stopTraining() {
    return this.req({path: '/api/training', method: 'DELETE'})
  }

  async getEntities() {
    return this.req({path: '/api/entities', method: 'GET'})
  }

  connectWS() {
    this.ws = new WebSocket('ws://localhost:8000/ws');

    this.ws.onopen = this.onopenWS.bind(this);
    this.ws.onmessage = this.onmessageWS.bind(this);
  }

  onopenWS(event) {
    const msg = {type: 'ping'};
    this.ws.send(JSON.stringify(msg));
  }

  onmessageWS(event) {
    const {type, payload} = JSON.parse(event.data)
    const whitelist = [
      'pong',
      'room',
      'training',
    ];
    if (whitelist.includes(type)) {
      this.dispatchEvent(new CustomEvent(type, {detail: payload}));
    }
  }
}

const restClient = new RESTClient()
restClient.addEventListener('pong', () => console.log('pong'))
restClient.addEventListener('room', msgRoomHandler)
restClient.addEventListener('training', msgTrainingHandler)
restClient.connectWS()

let deviceId = null
let isGathering = false
let isTraining = false

function empty(element) {
  while (element.firstElementChild) {
    element.firstElementChild.remove();
  }
}

function createDeviceHTMLEntry(device) {
  const li = document.createElement('li')
  const button = document.createElement('button')
  button.classList.add(...'waves-effect waves-light btn-large'.split(' '))
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

function hideActionDetails() {
  const elList = [...document.querySelectorAll('#actionDetails > div')];
  for (const el of elList) {
    el.classList.add('hidden')
  }
}

function showActionDetails(id) {
  hideActionDetails();
  const el = document.getElementById(id)
  el.classList.remove('hidden');
}

async function toggleGathering(el) {
  el.disabled = true
  if (isGathering) {
    await restClient.stopGathering(deviceId);
  }
  else {
    showActionDetails('gatheringDetails');
    const el =
        document.querySelector('input[type=radio][name=gatheringMode]:checked')
    const action = el.value;
    await restClient.startGathering(action, deviceId);
  }
  isGathering = !isGathering
  el.innerText = isGathering ? 'Stop Gathering' : 'Start Gathering'
  el.disabled = false
}

async function toggleTraining(el) {
  el.disabled = true;
  if (isGathering) {
    await restClient.stopTraining();
  } else {
    const el =
        document.querySelector('input[type=radio][name=trainingMode]:checked')
    const optimize = el.value === 'Optimize'
    showActionDetails('trainingDetails');
    await restClient.startTraining(optimize, deviceId);
  }
  isTraining = !isTraining
  el.innerText = isTraining ? 'Stop Training' : 'Start Training'
  el.disabled = false
}

function msgRoomHandler(e) {
  const msg = e.detail
  if (msg.deviceId !== deviceId) return;
  const el = document.getElementById('room')
  el.innerText = msg.room
}

function msgTrainingHandler(e) {
  const msg = e.detail
  const trainingDetailsEl = document.getElementById('trainingDetails')
  if (msg.state === 'started') {
    trainingDetailsEl.classList.add('training')
  }
  if (msg.state === 'finished') {
    const startStopTrainingBtnEl =
        document.getElementById('startStopTrainingBtn')
    isTraining = false
    startStopTrainingBtnEl.innerText = 'Start Training'
    startStopTrainingBtnEl.disabled = false
    trainingDetailsEl.classList.remove('training')
    const trainingDetailsTextEl =
        document.querySelector('#trainingDetails .text')
    trainingDetailsTextEl.innerText =
        Object.keys(msg.stats)
            .map(x => `${x}: ${msg.stats[x] || 'N/A'}`)
            .join('\n')
  }
}

async function changeRoom(room) {
  await restClient.changeRoom(room, deviceId)
}

async function updateEntites() {
  const entities = await restClient.getEntities()
  populateEntities(entities)
}

async function main() {
  await updateEntites()
}

addEventListener('DOMContentLoaded', main);