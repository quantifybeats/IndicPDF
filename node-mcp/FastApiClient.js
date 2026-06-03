const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');

class FastApiClient {
    constructor(baseUrl, apiKey) {
        this.client = axios.create({
            baseURL: baseUrl,
            headers: {
                'X-API-Key': apiKey
            }
        });
    }

    async upload(fileStream, filename) {
        const form = new FormData();
        form.append('files', fileStream, { filename });

        const response = await this.client.post('/upload', form, {
            headers: {
                ...form.getHeaders()
            }
        });
        
        // Return the first job ID from the array
        return response.data.jobs[0].job_id;
    }

    async getStatus(jobId) {
        const response = await this.client.get(`/status/${jobId}`);
        return response.data;
    }

    async pollStatus(jobId, interval = 2000, timeout = 60000) {
        const start = Date.now();
        while (Date.now() - start < timeout) {
            const data = await this.getStatus(jobId);
            if (data.status === 'finished') {
                return data;
            }
            if (data.status === 'failed') {
                throw new Error(`Job ${jobId} failed: ${data.exc_info || 'Unknown error'}`);
            }
            await new Promise(resolve => setTimeout(resolve, interval));
        }
        throw new Error(`Polling timeout for job ${jobId}`);
    }

    async download(jobId) {
        const response = await this.client.get(`/download/${jobId}`, {
            responseType: 'arraybuffer'
        });
        return response.data;
    }
}

module.exports = FastApiClient;
