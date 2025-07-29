let allPhotos = [];
let currentYear = new Date().getFullYear();
let currentTag = null;
let photoPlacemarks = [];
let clusterPlacemarks = [];
let contextMenu;
let userLocationPlacemark = null;

let placemarkCache = {};

const yearSlider = document.getElementById('yearSlider');
const currentYearDisplay = document.getElementById('currentYearDisplay');
const tagsList = document.getElementById('tagsList');
const eventsToggle = document.getElementById('eventsToggle');

ymaps.ready(init);

let map;

function init() {
  map = new ymaps.Map("map", {
    center: [55.7558, 37.6173],
    zoom: 10,
    controls: ['zoomControl', 'geolocationControl']
  });

  map.events.add('boundschange', () => {
    loadPhotos();
  });

  map.events.add('contextmenu', (e) => {
    const coords = e.get('coords');
    const originalEvent = e.get('domEvent').originalEvent;
    const target = originalEvent.target;

    if (target.closest('.cluster-marker')) return;

    removeContextMenu();

    contextMenu = document.createElement('div');
    contextMenu.className = 'context-menu';
    contextMenu.style.top = `${originalEvent.clientY}px`;
    contextMenu.style.left = `${originalEvent.clientX}px`;

    const addBtn = document.createElement('button');
    addBtn.textContent = 'Добавить фото';
    addBtn.onclick = () => {
      if (window.userIsAuthenticated) {
        window.location.href = `/upload/?lat=${coords[0]}&lon=${coords[1]}`;
      } else {
        alert("Авторизуйтесь, чтобы добавить фото");
      }
      removeContextMenu();
    };


    contextMenu.appendChild(addBtn);
    document.body.appendChild(contextMenu);

    document.addEventListener('click', function handler(event) {
      if (!contextMenu.contains(event.target)) {
        removeContextMenu();
        document.removeEventListener('click', handler);
      }
    });
  });

  eventsToggle.addEventListener('click', () => {
    tagsList.classList.toggle('show');
  });

  yearSlider.addEventListener('input', handleYearChange);

  loadTags();
  loadPhotos();
}

function handleYearChange() {
  currentYear = parseInt(yearSlider.value);
  currentTag = null;
  currentYearDisplay.textContent = (currentYear === new Date().getFullYear()) ? "Все года" : currentYear;
  placemarkCache = {};
  loadPhotos();
}

async function loadPhotos() {
  const bounds = map.getBounds();
  const sw = bounds[0];
  const ne = bounds[1];
  const bbox = `${sw[0]},${sw[1]},${ne[0]},${ne[1]}`;

  let url = `/api/photos/geojson/?bbox=${bbox}`;
  if (currentTag) url += `&tag=${currentTag}`;
  else if (currentYear !== new Date().getFullYear()) url += `&year=${currentYear}`;

  const res = await fetch(url);
  const data = await res.json();
  allPhotos = data.features;
  renderMarkers();
}


function renderMarkers() {
  map.geoObjects.removeAll();

  if (userLocationPlacemark) {
    map.geoObjects.add(userLocationPlacemark);
  }

  photoPlacemarks = [];
  clusterPlacemarks = [];

  const zoom = map.getZoom();
  const clusters = clusterizePoints(allPhotos, zoom);

  clusters.forEach(cluster => {
    if (cluster.points.length === 1) {
      const point = cluster.points[0];
      const id = point.properties.id;

      if (!placemarkCache[id]) {
        placemarkCache[id] = createPhotoPlacemark(point);
      }

      const placemark = placemarkCache[id];
      photoPlacemarks.push(placemark);
      map.geoObjects.add(placemark);
    } else {
      const clusterMark = createClusterPlacemark(cluster);
      clusterPlacemarks.push(clusterMark);
      map.geoObjects.add(clusterMark);
    }
  });
}

function clusterizePoints(points, zoom) {
  const gridSize = 0.04 / Math.pow(2, zoom - 10);
  const clusters = [];

  points.forEach((point) => {
    const coords = point.geometry.coordinates.slice().reverse();
    let cluster = clusters.find(c =>
      Math.abs(c.center[0] - coords[0]) < gridSize &&
      Math.abs(c.center[1] - coords[1]) < gridSize
    );

    if (cluster) {
      cluster.points.push(point);
    } else {
      clusters.push({ center: coords, points: [point] });
    }
  });

  return clusters;
}

function createPhotoPlacemark(feature) {
  const coords = feature.geometry.coordinates.slice().reverse();
  const props = feature.properties;

  const layout = ymaps.templateLayoutFactory.createClass(
    `<div class="cluster-marker ${currentTag && currentTag === props.tag ? 'filtered' : ''}" style="border: 2px solid ${currentTag && currentTag === props.tag ? '#4CAF50' : '#000'};">
      <img src="${props.image}" />
    </div>`
  );

  const placemark = new ymaps.Placemark(coords, props, {
    iconLayout: layout,
    iconShape: {
      type: 'Circle',
      coordinates: [25, 25],
      radius: 25,
    },
    zIndex: 1000
  });

  placemark.events.add('click', () => {
    window.location.href = `/photo/${props.id}`;
  });

  placemark.events.add('contextmenu', (e) => {
    e.preventDefault();
    e.stopPropagation();
    showMarkerContextMenu(e.get('domEvent').originalEvent, props);
  });

  return placemark;
}

function createClusterPlacemark(cluster) {
  const firstWithImage = cluster.points.find(p => p.properties.image);
  const firstWithTag = cluster.points.find(p => p.properties.tag);
  const firstImage = firstWithImage ? firstWithImage.properties.image : '/static/default.jpg';
  const count = cluster.points.length;
  const tag = firstWithTag ? firstWithTag.properties.tag : null;
  const isFiltered = currentTag && tag === currentTag;

  const layout = ymaps.templateLayoutFactory.createClass(
    `<div class="cluster-marker ${isFiltered ? 'filtered' : ''}" style="border: 2px solid ${isFiltered ? '#4CAF50' : '#000'};">
      <img src="${firstImage}" />
      <span>${count}</span>
    </div>`
  );

  const placemark = new ymaps.Placemark(cluster.center, {
    tag: tag
  }, {
    iconLayout: layout,
    iconShape: {
      type: 'Circle',
      coordinates: [25, 25],
      radius: 25,
    },
    zIndex: 999
  });

  placemark.events.add('click', () => {
    const currentZoom = map.getZoom();
    const targetZoom = Math.min(currentZoom + 3, 20);
    map.setCenter(cluster.center, targetZoom);
  });

  placemark.events.add('contextmenu', (e) => {
    e.preventDefault();
    e.stopPropagation();
    showClusterContextMenu(e.get('domEvent').originalEvent, tag);
  });

  return placemark;
}

function removeContextMenu() {
  if (contextMenu) {
    contextMenu.remove();
    contextMenu = null;
  }
}

function showMarkerContextMenu(e, props) {
  removeContextMenu();

  contextMenu = document.createElement('div');
  contextMenu.className = 'context-menu';
  contextMenu.style.top = `${e.clientY}px`;
  contextMenu.style.left = `${e.clientX}px`;

  if (currentTag) {
    const resetBtn = document.createElement('button');
    resetBtn.textContent = 'Сбросить фильтр';
    resetBtn.onclick = () => {
      currentTag = null;
      currentYear = new Date().getFullYear();
      yearSlider.value = currentYear;
      currentYearDisplay.textContent = "Все года";
      placemarkCache = {};
      loadPhotos();
      removeContextMenu();
    };
    contextMenu.appendChild(resetBtn);
  } else if (props.tag) {
    const tagBtn = document.createElement('button');
    tagBtn.textContent = 'Посмотреть событие';
    tagBtn.onclick = () => {
      currentTag = props.tag;
      placemarkCache = {};
      loadPhotos();
      removeContextMenu();
    };
    contextMenu.appendChild(tagBtn);
  }

  document.body.appendChild(contextMenu);
  document.addEventListener('click', function handler(event) {
    if (!contextMenu.contains(event.target)) {
      removeContextMenu();
      document.removeEventListener('click', handler);
    }
  });
}

function showClusterContextMenu(e, tag) {
  removeContextMenu();

  contextMenu = document.createElement('div');
  contextMenu.className = 'context-menu';
  contextMenu.style.top = `${e.clientY}px`;
  contextMenu.style.left = `${e.clientX}px`;

  if (currentTag) {
    const resetBtn = document.createElement('button');
    resetBtn.textContent = 'Сбросить фильтр';
    resetBtn.onclick = () => {
      currentTag = null;
      currentYear = new Date().getFullYear();
      yearSlider.value = currentYear;
      currentYearDisplay.textContent = "Все года";
      placemarkCache = {};
      loadPhotos();
      removeContextMenu();
    };
    contextMenu.appendChild(resetBtn);
  } else if (tag) {
    const tagBtn = document.createElement('button');
    tagBtn.textContent = 'Посмотреть событие';
    tagBtn.onclick = () => {
      currentTag = tag;
      placemarkCache = {};
      loadPhotos();
      removeContextMenu();
    };
    contextMenu.appendChild(tagBtn);
  }

  document.body.appendChild(contextMenu);
  document.addEventListener('click', function handler(event) {
    if (!contextMenu.contains(event.target)) {
      removeContextMenu();
      document.removeEventListener('click', handler);
    }
  });
}

async function loadTags() {
  const res = await fetch('/api/user-tags/');
  const tags = await res.json();
  tagsList.innerHTML = '';

  const clearBtn = document.createElement('button');
  clearBtn.textContent = 'Сбросить фильтр';
  clearBtn.classList.add('clear-tag-button');
  clearBtn.onclick = () => {
    currentTag = null;
    currentYear = new Date().getFullYear();
    yearSlider.value = currentYear;
    currentYearDisplay.textContent = "Все года";
    placemarkCache = {};
    loadPhotos();
  };
  tagsList.appendChild(clearBtn);

  tags.forEach(tag => {
    const btn = document.createElement('button');
    btn.textContent = tag;
    btn.classList.add('tag-button');
    btn.onclick = () => {
      currentTag = tag;
      placemarkCache = {};
      loadPhotos();
      tagsList.classList.remove('show');
    };
    tagsList.appendChild(btn);
  });
}

window.locateUser = function () {
  if (!navigator.geolocation) {
    alert('Геолокация не поддерживается вашим браузером');
    return;
  }

  navigator.geolocation.getCurrentPosition((position) => {
    const coords = [position.coords.latitude, position.coords.longitude];

    if (!userLocationPlacemark) {
      userLocationPlacemark = new ymaps.Placemark(coords, {}, {
        preset: 'islands#circleIcon',
        iconColor: '#ff0000',
        zIndex: 2000
      });
      map.geoObjects.add(userLocationPlacemark);
    } else {
      userLocationPlacemark.geometry.setCoordinates(coords);
    }

    map.setCenter(coords, 15, { duration: 300 });
  }, () => {
    alert('Не удалось получить ваше местоположение');
  });
};
