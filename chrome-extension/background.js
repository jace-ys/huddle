chrome.runtime.onInstalled.addListener(() => {
  console.log("Installed");
  chrome.declarativeContent.onPageChanged.removeRules(undefined, function() {
      chrome.declarativeContent.onPageChanged.addRules([{
        conditions: [new chrome.declarativeContent.PageStateMatcher({
          pageUrl: {hostEquals: 'trello.com'},
        })],
        actions: [new chrome.declarativeContent.ShowPageAction()]
      }]);
    });
});
