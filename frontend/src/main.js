import { createApp } from 'vue'
import { library } from '@fortawesome/fontawesome-svg-core'
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome'
import {
  faBars,
  faRightFromBracket,
  faXmark,
  faPlus,
  faPaperclip,
  faChevronDown,
  faGlobe,
  faDatabase,
  faPlug,
  faWandMagicSparkles,
  faHouse,
  faUser,
  faSitemap,
  faUserShield,
  faUsers,
  faFileSignature,
  faSms,
  faMagnifyingGlass,
  faServer,
  faBook,
  faComment,
  faRobot,
  faComments,
  faSliders,
  faFileLines,
  faLock,
  faGear,
  faShareNodes,
  faChartLine,
} from '@fortawesome/free-solid-svg-icons'
import './style.css'
import App from './App.vue'
import router from './router'

library.add(faBars, faRightFromBracket, faXmark, faPlus, faPaperclip, faChevronDown, faGlobe, faDatabase, faPlug, faWandMagicSparkles, faHouse, faUser, faSitemap, faUserShield, faUsers, faFileSignature, faSms, faMagnifyingGlass, faServer, faBook, faComment, faRobot, faComments, faSliders, faFileLines, faLock, faGear, faShareNodes, faChartLine)

createApp(App).component('font-awesome-icon', FontAwesomeIcon).use(router).mount('#app')
