import http from 'node:http';
import {parse} from 'node:url';
import {createRequire} from 'node:module';
import {afterEach, expect, it, vi} from 'vitest';
import nextConfig from '../../next.config.mjs';

const require = createRequire(import.meta.url);
const {proxyRequest} = require('next/dist/server/lib/router-utils/proxy-request.js');
const servers = [];
const timers = [];

afterEach(async()=>{
  timers.forEach(clearTimeout);timers.length=0;
  await Promise.all(servers.splice(0).map(server=>new Promise(resolve=>{
    server.closeAllConnections();server.close(resolve);
  })));
  vi.restoreAllMocks();
});

async function requestThroughProxy(delay, status, body) {
  const errors = [];
  const backend = http.createServer((req,res)=>{
    expect(req.method).toBe('POST');
    expect(req.url).toBe('/api/matches/synthetic/ai?force=true');
    req.resume();
    timers.push(setTimeout(()=>{
      res.writeHead(status,{'Content-Type':'application/json'});
      res.end(JSON.stringify(body));
    },delay));
  });
  servers.push(backend);
  await new Promise(resolve=>backend.listen(0,'127.0.0.1',resolve));
  const frontend = http.createServer((req,res)=>{
    const target = parse(`http://127.0.0.1:${backend.address().port}${req.url}`,true);
    proxyRequest(req,res,target,undefined,undefined,nextConfig.experimental?.proxyTimeout)
      .catch(error=>errors.push(error.code));
  });
  servers.push(frontend);
  await new Promise(resolve=>frontend.listen(0,'127.0.0.1',resolve));
  const result = await new Promise((resolve,reject)=>{
    const request = http.request({hostname:'127.0.0.1',port:frontend.address().port,
      path:'/api/matches/synthetic/ai?force=true',method:'POST'},response=>{
      let data='';response.setEncoding('utf8');response.on('data',chunk=>{data+=chunk;});
      response.on('end',()=>resolve({status:response.statusCode,body:data}));
    });
    request.on('error',reject);request.end();
  });
  expect(errors).toEqual([]);
  return result;
}

it('passes a forced AI response taking longer than Next’s former 30-second timeout',async()=>{
  vi.spyOn(console,'error').mockImplementation(()=>{});
  const result=await requestThroughProxy(31_000,200,{ai_analysis:{cached:false}});
  expect(result.status).toBe(200);
  expect(JSON.parse(result.body).ai_analysis.cached).toBe(false);
},45_000);

it('preserves the backend safe invalid-output response instead of creating a proxy 500',async()=>{
  const result=await requestThroughProxy(5,502,{error:{code:'AI_INVALID_OUTPUT',message:'Invalid AI output.'}});
  expect(result.status).toBe(502);
  expect(JSON.parse(result.body).error.code).toBe('AI_INVALID_OUTPUT');
});
