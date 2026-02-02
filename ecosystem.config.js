module.exports = {
    apps: [{
        name: 'n8n',
        script: './packages/cli/bin/n8n',
        cwd: 'W:/1_DXP_Projects/14_Automation/n8n',
        env: {
            N8N_COMMUNITY_PACKAGES_ENABLED: 'true',
            N8N_DEFAULT_LOCALE: 'ko',
            NODE_ENV: 'production'
        },
        autorestart: true,
        watch: false,
        max_memory_restart: '1G',
        log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
        error_file: 'W:/1_DXP_Projects/14_Automation/n8n/logs/error.log',
        out_file: 'W:/1_DXP_Projects/14_Automation/n8n/logs/out.log',
        merge_logs: true
    }]
};
