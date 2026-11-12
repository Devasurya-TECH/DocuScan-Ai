import axios from 'axios'

// OCR currently evaluates multiple image variants synchronously. A larger
// phone image can legitimately take longer than Axios's default short timeout.
const api = axios.create({ baseURL: '/api', timeout: 120000 })
export default api
