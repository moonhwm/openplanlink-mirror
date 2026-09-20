exports.main = async (event, context) => {
  const results = {};
  
  try {
    const cloudbase = require('@cloudbase/node-sdk');
    const app = cloudbase.init({ env: 'a2a-commonwealth-d2eepjr928e9c4d' });
    
    // Upload a test file
    const testContent = JSON.stringify({ items: [], serverTs: 0 });
    const uploadResult = await app.uploadFile({
      cloudPath: 'alerts/alerts.json',
      fileContent: Buffer.from(testContent, 'utf-8'),
    });
    results.uploadResult = JSON.stringify(uploadResult);
    results.fileID = uploadResult.fileID;
    
    // Now try to download using the fileID
    const downloadResult = await app.downloadFile({
      fileID: uploadResult.fileID,
    });
    results.downloadSuccess = true;
    results.downloadContent = downloadResult.fileContent.toString('utf-8');
    
    // Try getTempFileURL
    const tempUrlResult = await app.getTempFileURL({
      fileList: [uploadResult.fileID],
    });
    results.tempUrlResult = JSON.stringify(tempUrlResult).substring(0, 500);
    
  } catch (e) {
    results.error = e.message;
  }
  
  return results;
};
