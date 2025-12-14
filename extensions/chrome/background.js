// background.js (키워드 차단 강화 버전)

// 1. 알람 생성
chrome.runtime.onInstalled.addListener(() => createAlarm());
chrome.runtime.onStartup.addListener(() => createAlarm());

function createAlarm() {
    chrome.alarms.create("checkServer", { periodInMinutes: 0.05 });
}

// 2. 알람 리스너
chrome.alarms.onAlarm.addListener((alarm) => {
    if (alarm.name === "checkServer") {
        checkStatus();
    }
});

// 3. 상태 체크 및 차단 로직
async function checkStatus() {
    try {
        const response = await fetch('http://127.0.0.1:5000/status', {
            cache: 'no-store'
        });
        
        if (!response.ok) return;

        const data = await response.json();

        if (data.blocking) {
            chrome.tabs.query({}, function(tabs) {
                tabs.forEach(tab => {
                    if (!tab.url) return;
                    
                    // 차단 페이지는 검사 제외
                    if (tab.url.includes("block.html")) return;

                    // [핵심 변경] URL과 키워드를 모두 소문자로 변환하여 비교 (대소문자 무시)
                    const currentUrl = tab.url.toLowerCase();
                    
                    // 하나라도 포함되어 있으면 차단 (Keyword Matching)
                    const isBlocked = data.sites.some(keyword => {
                        // 빈 칸이나 너무 짧은 키워드(1글자)는 오작동 방지를 위해 무시 가능
                        if (keyword.trim().length < 2) return false; 
                        return currentUrl.includes(keyword.toLowerCase());
                    });

                    if (isBlocked) {
                        const blockPageUrl = chrome.runtime.getURL("block.html");
                        chrome.tabs.update(tab.id, { url: blockPageUrl });
                    }
                });
            });
        }
    } catch (error) {
        // console.log("Python App disconnect");
    }
}