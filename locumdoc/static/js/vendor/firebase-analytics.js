var Se=()=>{};var De=function(e){let t=[],n=0;for(let r=0;r<e.length;r++){let i=e.charCodeAt(r);i<128?t[n++]=i:i<2048?(t[n++]=i>>6|192,t[n++]=i&63|128):(i&64512)===55296&&r+1<e.length&&(e.charCodeAt(r+1)&64512)===56320?(i=65536+((i&1023)<<10)+(e.charCodeAt(++r)&1023),t[n++]=i>>18|240,t[n++]=i>>12&63|128,t[n++]=i>>6&63|128,t[n++]=i&63|128):(t[n++]=i>>12|224,t[n++]=i>>6&63|128,t[n++]=i&63|128)}return t},_t=function(e){let t=[],n=0,r=0;for(;n<e.length;){let i=e[n++];if(i<128)t[r++]=String.fromCharCode(i);else if(i>191&&i<224){let s=e[n++];t[r++]=String.fromCharCode((i&31)<<6|s&63)}else if(i>239&&i<365){let s=e[n++],a=e[n++],o=e[n++],c=((i&7)<<18|(s&63)<<12|(a&63)<<6|o&63)-65536;t[r++]=String.fromCharCode(55296+(c>>10)),t[r++]=String.fromCharCode(56320+(c&1023))}else{let s=e[n++],a=e[n++];t[r++]=String.fromCharCode((i&15)<<12|(s&63)<<6|a&63)}}return t.join("")},Te={byteToCharMap_:null,charToByteMap_:null,byteToCharMapWebSafe_:null,charToByteMapWebSafe_:null,ENCODED_VALS_BASE:"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",get ENCODED_VALS(){return this.ENCODED_VALS_BASE+"+/="},get ENCODED_VALS_WEBSAFE(){return this.ENCODED_VALS_BASE+"-_."},HAS_NATIVE_SUPPORT:typeof atob=="function",encodeByteArray(e,t){if(!Array.isArray(e))throw Error("encodeByteArray takes an array as a parameter");this.init_();let n=t?this.byteToCharMapWebSafe_:this.byteToCharMap_,r=[];for(let i=0;i<e.length;i+=3){let s=e[i],a=i+1<e.length,o=a?e[i+1]:0,c=i+2<e.length,l=c?e[i+2]:0,h=s>>2,u=(s&3)<<4|o>>4,A=(o&15)<<2|l>>6,p=l&63;c||(p=64,a||(A=64)),r.push(n[h],n[u],n[A],n[p])}return r.join("")},encodeString(e,t){return this.HAS_NATIVE_SUPPORT&&!t?btoa(e):this.encodeByteArray(De(e),t)},decodeString(e,t){return this.HAS_NATIVE_SUPPORT&&!t?atob(e):_t(this.decodeStringToByteArray(e,t))},decodeStringToByteArray(e,t){this.init_();let n=t?this.charToByteMapWebSafe_:this.charToByteMap_,r=[];for(let i=0;i<e.length;){let s=n[e.charAt(i++)],o=i<e.length?n[e.charAt(i)]:0;++i;let l=i<e.length?n[e.charAt(i)]:64;++i;let u=i<e.length?n[e.charAt(i)]:64;if(++i,s==null||o==null||l==null||u==null)throw new z;let A=s<<2|o>>4;if(r.push(A),l!==64){let p=o<<4&240|l>>2;if(r.push(p),u!==64){let It=l<<6&192|u;r.push(It)}}}return r},init_(){if(!this.byteToCharMap_){this.byteToCharMap_={},this.charToByteMap_={},this.byteToCharMapWebSafe_={},this.charToByteMapWebSafe_={};for(let e=0;e<this.ENCODED_VALS.length;e++)this.byteToCharMap_[e]=this.ENCODED_VALS.charAt(e),this.charToByteMap_[this.byteToCharMap_[e]]=e,this.byteToCharMapWebSafe_[e]=this.ENCODED_VALS_WEBSAFE.charAt(e),this.charToByteMapWebSafe_[this.byteToCharMapWebSafe_[e]]=e,e>=this.ENCODED_VALS_BASE.length&&(this.charToByteMap_[this.ENCODED_VALS_WEBSAFE.charAt(e)]=e,this.charToByteMapWebSafe_[this.ENCODED_VALS.charAt(e)]=e)}}},z=class extends Error{constructor(){super(...arguments),this.name="DecodeBase64StringError"}},Et=function(e){let t=De(e);return Te.encodeByteArray(t,!0)},j=function(e){return Et(e).replace(/\./g,"")},Oe=function(e){try{return Te.decodeString(e,!0)}catch(t){console.error("base64Decode failed: ",t)}return null};function vt(){if(typeof self!="undefined")return self;if(typeof window!="undefined")return window;if(typeof global!="undefined")return global;throw new Error("Unable to locate global object.")}var At=()=>vt().__FIREBASE_DEFAULTS__,St=()=>{if(typeof process=="undefined"||typeof process.env=="undefined")return;let e=process.env.__FIREBASE_DEFAULTS__;if(e)return JSON.parse(e)},Ct=()=>{if(typeof document=="undefined")return;let e;try{e=document.cookie.match(/__FIREBASE_DEFAULTS__=([^;]+)/)}catch{return}let t=e&&Oe(e[1]);return t&&JSON.parse(t)},Dt=()=>{try{return Se()||At()||St()||Ct()}catch(e){console.info(`Unable to get __FIREBASE_DEFAULTS__ due to: ${e}`);return}};var xe=()=>{var e;return(e=Dt())==null?void 0:e.config};var M=class{constructor(){this.reject=()=>{},this.resolve=()=>{},this.promise=new Promise((t,n)=>{this.resolve=t,this.reject=n})}wrapCallback(t){return(n,r)=>{n?this.reject(n):this.resolve(r),typeof t=="function"&&(this.promise.catch(()=>{}),t.length===1?t(n):t(n,r))}}};function W(){let e=typeof chrome=="object"?chrome.runtime:typeof browser=="object"?browser.runtime:void 0;return typeof e=="object"&&e.id!==void 0}function R(){try{return typeof indexedDB=="object"}catch{return!1}}function N(){return new Promise((e,t)=>{try{let n=!0,r="validate-browser-context-for-indexeddb-analytics-module",i=self.indexedDB.open(r);i.onsuccess=()=>{i.result.close(),n||self.indexedDB.deleteDatabase(r),e(!0)},i.onupgradeneeded=()=>{n=!1},i.onerror=()=>{var s;t(((s=i.error)==null?void 0:s.message)||"")}}catch(n){t(n)}})}function q(){return!(typeof navigator=="undefined"||!navigator.cookieEnabled)}var Tt="FirebaseError",b=class e extends Error{constructor(t,n,r){super(n),this.code=t,this.customData=r,this.name=Tt,Object.setPrototypeOf(this,e.prototype),Error.captureStackTrace&&Error.captureStackTrace(this,I.prototype.create)}},I=class{constructor(t,n,r){this.service=t,this.serviceName=n,this.errors=r}create(t,...n){let r=n[0]||{},i=`${this.service}/${t}`,s=this.errors[t],a=s?Ot(s,r):"Error",o=`${this.serviceName}: ${a} (${i}).`;return new b(i,o,r)}};function Ot(e,t){try{let n=0,r="";for(;n<e.length;){let i=e.indexOf("{$",n);if(i===-1){r+=e.substring(n);break}let s=e.indexOf("}",i+2);if(s===-1){r+=e.substring(n);break}let a=e.substring(i+2,s),o=t[a];r+=e.substring(n,i)+(o!=null?String(o):`<${a}?>`),n=s+1}return r}catch{return e}}function O(e,t){if(e===t)return!0;let n=Object.keys(e),r=Object.keys(t);for(let i of n){if(!r.includes(i))return!1;let s=e[i],a=t[i];if(Ce(s)&&Ce(a)){if(!O(s,a))return!1}else if(s!==a)return!1}for(let i of r)if(!n.includes(i))return!1;return!0}function Ce(e){return e!==null&&typeof e=="object"}var xt=1e3,kt=2,Rt=14400*1e3,Nt=.5;function G(e,t=xt,n=kt){let r=t*Math.pow(n,e),i=Math.round(Nt*r*(Math.random()-.5)*2);return Math.min(Rt,r+i)}function K(e){return e&&e._delegate?e._delegate:e}var m=class{constructor(t,n,r){this.name=t,this.instanceFactory=n,this.type=r,this.multipleInstances=!1,this.serviceProps={},this.instantiationMode="LAZY",this.onInstanceCreated=null}setInstantiationMode(t){return this.instantiationMode=t,this}setMultipleInstances(t){return this.multipleInstances=t,this}setServiceProps(t){return this.serviceProps=t,this}setInstanceCreatedCallback(t){return this.onInstanceCreated=t,this}};var S="[DEFAULT]";var J=class{constructor(t,n){this.name=t,this.container=n,this.component=null,this.instances=new Map,this.instancesDeferred=new Map,this.instancesOptions=new Map,this.onInitCallbacks=new Map}get(t){let n=this.normalizeInstanceIdentifier(t);if(!this.instancesDeferred.has(n)){let r=new M;if(this.instancesDeferred.set(n,r),this.isInitialized(n)||this.shouldAutoInitialize())try{let i=this.getOrInitializeService({instanceIdentifier:n});i&&r.resolve(i)}catch{}}return this.instancesDeferred.get(n).promise}getImmediate(t){var i;let n=this.normalizeInstanceIdentifier(t==null?void 0:t.identifier),r=(i=t==null?void 0:t.optional)!=null?i:!1;if(this.isInitialized(n)||this.shouldAutoInitialize())try{return this.getOrInitializeService({instanceIdentifier:n})}catch(s){if(r)return null;throw s}else{if(r)return null;throw Error(`Service ${this.name} is not available`)}}getComponent(){return this.component}setComponent(t){if(t.name!==this.name)throw Error(`Mismatching Component ${t.name} for Provider ${this.name}.`);if(this.component)throw Error(`Component for ${this.name} has already been provided`);if(this.component=t,!!this.shouldAutoInitialize()){if(Pt(t))try{this.getOrInitializeService({instanceIdentifier:S})}catch{}for(let[n,r]of this.instancesDeferred.entries()){let i=this.normalizeInstanceIdentifier(n);try{let s=this.getOrInitializeService({instanceIdentifier:i});r.resolve(s)}catch{}}}}clearInstance(t=S){this.instancesDeferred.delete(t),this.instancesOptions.delete(t),this.instances.delete(t)}async delete(){let t=Array.from(this.instances.values());await Promise.all([...t.filter(n=>"INTERNAL"in n).map(n=>n.INTERNAL.delete()),...t.filter(n=>"_delete"in n).map(n=>n._delete())])}isComponentSet(){return this.component!=null}isInitialized(t=S){return this.instances.has(t)}getOptions(t=S){return this.instancesOptions.get(t)||{}}initialize(t={}){let{options:n={}}=t,r=this.normalizeInstanceIdentifier(t.instanceIdentifier);if(this.isInitialized(r))throw Error(`${this.name}(${r}) has already been initialized`);if(!this.isComponentSet())throw Error(`Component ${this.name} has not been registered yet`);let i=this.getOrInitializeService({instanceIdentifier:r,options:n});for(let[s,a]of this.instancesDeferred.entries()){let o=this.normalizeInstanceIdentifier(s);r===o&&a.resolve(i)}return i}onInit(t,n){var a;let r=this.normalizeInstanceIdentifier(n),i=(a=this.onInitCallbacks.get(r))!=null?a:new Set;i.add(t),this.onInitCallbacks.set(r,i);let s=this.instances.get(r);return s&&t(s,r),()=>{i.delete(t)}}invokeOnInitCallbacks(t,n){let r=this.onInitCallbacks.get(n);if(r)for(let i of r)try{i(t,n)}catch{}}getOrInitializeService({instanceIdentifier:t,options:n={}}){let r=this.instances.get(t);if(!r&&this.component&&(r=this.component.instanceFactory(this.container,{instanceIdentifier:Bt(t),options:n}),this.instances.set(t,r),this.instancesOptions.set(t,n),this.invokeOnInitCallbacks(r,t),this.component.onInstanceCreated))try{this.component.onInstanceCreated(this.container,t,r)}catch{}return r||null}normalizeInstanceIdentifier(t=S){return this.component?this.component.multipleInstances?t:S:t}shouldAutoInitialize(){return!!this.component&&this.component.instantiationMode!=="EXPLICIT"}};function Bt(e){return e===S?void 0:e}function Pt(e){return e.instantiationMode==="EAGER"}var $=class{constructor(t){this.name=t,this.providers=new Map}addComponent(t){let n=this.getProvider(t.name);if(n.isComponentSet())throw new Error(`Component ${t.name} has already been registered with ${this.name}`);n.setComponent(t)}addOrOverwriteComponent(t){this.getProvider(t.name).isComponentSet()&&this.providers.delete(t.name),this.addComponent(t)}getProvider(t){if(this.providers.has(t))return this.providers.get(t);let n=new J(t,this);return this.providers.set(t,n),n}getProviders(){return Array.from(this.providers.values())}};var Mt=[],f;(function(e){e[e.DEBUG=0]="DEBUG",e[e.VERBOSE=1]="VERBOSE",e[e.INFO=2]="INFO",e[e.WARN=3]="WARN",e[e.ERROR=4]="ERROR",e[e.SILENT=5]="SILENT"})(f||(f={}));var $t={debug:f.DEBUG,verbose:f.VERBOSE,info:f.INFO,warn:f.WARN,error:f.ERROR,silent:f.SILENT},Lt=f.INFO,Ft={[f.DEBUG]:"log",[f.VERBOSE]:"log",[f.INFO]:"info",[f.WARN]:"warn",[f.ERROR]:"error"},Ht=(e,t,...n)=>{if(t<e.logLevel)return;let r=new Date().toISOString(),i=Ft[t];if(i)console[i](`[${r}]  ${e.name}:`,...n);else throw new Error(`Attempted to log a message with an invalid logType (value: ${t})`)},x=class{constructor(t){this.name=t,this._logLevel=Lt,this._logHandler=Ht,this._userLogHandler=null,Mt.push(this)}get logLevel(){return this._logLevel}set logLevel(t){if(!(t in f))throw new TypeError(`Invalid value "${t}" assigned to \`logLevel\``);this._logLevel=t}setLogLevel(t){this._logLevel=typeof t=="string"?$t[t]:t}get logHandler(){return this._logHandler}set logHandler(t){if(typeof t!="function")throw new TypeError("Value assigned to `logHandler` must be a function");this._logHandler=t}get userLogHandler(){return this._userLogHandler}set userLogHandler(t){this._userLogHandler=t}debug(...t){this._userLogHandler&&this._userLogHandler(this,f.DEBUG,...t),this._logHandler(this,f.DEBUG,...t)}log(...t){this._userLogHandler&&this._userLogHandler(this,f.VERBOSE,...t),this._logHandler(this,f.VERBOSE,...t)}info(...t){this._userLogHandler&&this._userLogHandler(this,f.INFO,...t),this._logHandler(this,f.INFO,...t)}warn(...t){this._userLogHandler&&this._userLogHandler(this,f.WARN,...t),this._logHandler(this,f.WARN,...t)}error(...t){this._userLogHandler&&this._userLogHandler(this,f.ERROR,...t),this._logHandler(this,f.ERROR,...t)}};var Ut=(e,t)=>t.some(n=>e instanceof n),ke,Re;function Vt(){return ke||(ke=[IDBDatabase,IDBObjectStore,IDBIndex,IDBCursor,IDBTransaction])}function zt(){return Re||(Re=[IDBCursor.prototype.advance,IDBCursor.prototype.continue,IDBCursor.prototype.continuePrimaryKey])}var Ne=new WeakMap,X=new WeakMap,Be=new WeakMap,Y=new WeakMap,Z=new WeakMap;function jt(e){let t=new Promise((n,r)=>{let i=()=>{e.removeEventListener("success",s),e.removeEventListener("error",a)},s=()=>{n(w(e.result)),i()},a=()=>{r(e.error),i()};e.addEventListener("success",s),e.addEventListener("error",a)});return t.then(n=>{n instanceof IDBCursor&&Ne.set(n,e)}).catch(()=>{}),Z.set(t,e),t}function Wt(e){if(X.has(e))return;let t=new Promise((n,r)=>{let i=()=>{e.removeEventListener("complete",s),e.removeEventListener("error",a),e.removeEventListener("abort",a)},s=()=>{n(),i()},a=()=>{r(e.error||new DOMException("AbortError","AbortError")),i()};e.addEventListener("complete",s),e.addEventListener("error",a),e.addEventListener("abort",a)});X.set(e,t)}var Q={get(e,t,n){if(e instanceof IDBTransaction){if(t==="done")return X.get(e);if(t==="objectStoreNames")return e.objectStoreNames||Be.get(e);if(t==="store")return n.objectStoreNames[1]?void 0:n.objectStore(n.objectStoreNames[0])}return w(e[t])},set(e,t,n){return e[t]=n,!0},has(e,t){return e instanceof IDBTransaction&&(t==="done"||t==="store")?!0:t in e}};function Pe(e){Q=e(Q)}function qt(e){return e===IDBDatabase.prototype.transaction&&!("objectStoreNames"in IDBTransaction.prototype)?function(t,...n){let r=e.call(L(this),t,...n);return Be.set(r,t.sort?t.sort():[t]),w(r)}:zt().includes(e)?function(...t){return e.apply(L(this),t),w(Ne.get(this))}:function(...t){return w(e.apply(L(this),t))}}function Gt(e){return typeof e=="function"?qt(e):(e instanceof IDBTransaction&&Wt(e),Ut(e,Vt())?new Proxy(e,Q):e)}function w(e){if(e instanceof IDBRequest)return jt(e);if(Y.has(e))return Y.get(e);let t=Gt(e);return t!==e&&(Y.set(e,t),Z.set(t,e)),t}var L=e=>Z.get(e);function F(e,t,{blocked:n,upgrade:r,blocking:i,terminated:s}={}){let a=indexedDB.open(e,t),o=w(a);return r&&a.addEventListener("upgradeneeded",c=>{r(w(a.result),c.oldVersion,c.newVersion,w(a.transaction),c)}),n&&a.addEventListener("blocked",c=>n(c.oldVersion,c.newVersion,c)),o.then(c=>{s&&c.addEventListener("close",()=>s()),i&&c.addEventListener("versionchange",l=>i(l.oldVersion,l.newVersion,l))}).catch(()=>{}),o}var Kt=["get","getKey","getAll","getAllKeys","count"],Jt=["put","add","delete","clear"],ee=new Map;function Me(e,t){if(!(e instanceof IDBDatabase&&!(t in e)&&typeof t=="string"))return;if(ee.get(t))return ee.get(t);let n=t.replace(/FromIndex$/,""),r=t!==n,i=Jt.includes(n);if(!(n in(r?IDBIndex:IDBObjectStore).prototype)||!(i||Kt.includes(n)))return;let s=async function(a,...o){let c=this.transaction(a,i?"readwrite":"readonly"),l=c.store;return r&&(l=l.index(o.shift())),(await Promise.all([l[n](...o),i&&c.done]))[0]};return ee.set(t,s),s}Pe(e=>({...e,get:(t,n,r)=>Me(t,n)||e.get(t,n,r),has:(t,n)=>!!Me(t,n)||e.has(t,n)}));var ne=class{constructor(t){this.container=t}getPlatformInfoString(){return this.container.getProviders().map(n=>{if(Yt(n)){let r=n.getImmediate();return`${r.library}/${r.version}`}else return null}).filter(n=>n).join(" ")}};function Yt(e){let t=e.getComponent();return(t==null?void 0:t.type)==="VERSION"}var re="@firebase/app",$e="0.16.2";var _=new x("@firebase/app"),Xt="@firebase/app-compat",Qt="@firebase/analytics-compat",Zt="@firebase/analytics",en="@firebase/app-check-compat",tn="@firebase/app-check",nn="@firebase/auth",rn="@firebase/auth-compat",sn="@firebase/database",an="@firebase/data-connect",on="@firebase/database-compat",cn="@firebase/functions",ln="@firebase/functions-compat",fn="@firebase/installations",un="@firebase/installations-compat",dn="@firebase/messaging",hn="@firebase/messaging-compat",pn="@firebase/performance",mn="@firebase/performance-compat",gn="@firebase/remote-config",bn="@firebase/remote-config-compat",yn="@firebase/storage",wn="@firebase/storage-compat",In="@firebase/firestore",_n="@firebase/ai",En="@firebase/firestore-compat",vn="firebase";var An="[DEFAULT]",Sn={[re]:"fire-core",[Xt]:"fire-core-compat",[Zt]:"fire-analytics",[Qt]:"fire-analytics-compat",[tn]:"fire-app-check",[en]:"fire-app-check-compat",[nn]:"fire-auth",[rn]:"fire-auth-compat",[sn]:"fire-rtdb",[an]:"fire-data-connect",[on]:"fire-rtdb-compat",[cn]:"fire-fn",[ln]:"fire-fn-compat",[fn]:"fire-iid",[un]:"fire-iid-compat",[dn]:"fire-fcm",[hn]:"fire-fcm-compat",[pn]:"fire-perf",[mn]:"fire-perf-compat",[gn]:"fire-rc",[bn]:"fire-rc-compat",[yn]:"fire-gcs",[wn]:"fire-gcs-compat",[In]:"fire-fst",[En]:"fire-fst-compat",[_n]:"fire-vertex","fire-js":"fire-js",[vn]:"fire-js-all"};var ie=new Map,Cn=new Map,se=new Map;function Le(e,t){try{e.container.addComponent(t)}catch(n){_.debug(`Component ${t.name} failed to register with FirebaseApp ${e.name}`,n)}}function E(e){let t=e.name;if(se.has(t))return _.debug(`There were multiple attempts to register component ${t}.`),!1;se.set(t,e);for(let n of ie.values())Le(n,e);for(let n of Cn.values())Le(n,e);return!0}function P(e,t){let n=e.container.getProvider("heartbeat").getImmediate({optional:!0});return n&&n.triggerHeartbeat(),e.container.getProvider(t)}var Dn={"no-app":"No Firebase App '{$appName}' has been created - call initializeApp() first","bad-app-name":"Illegal App name: '{$appName}'","duplicate-app":"Firebase App named '{$appName}' already exists with different {$mismatchedParam}. Existing: '{$oldValue}'. New: '{$newValue}'.","app-deleted":"Firebase App named '{$appName}' already deleted","server-app-deleted":"Firebase Server App has been deleted","no-options":"Need to provide options, when not being deployed to hosting via source.","invalid-app-argument":"firebase.{$appName}() takes either no argument or a Firebase App instance.","invalid-log-argument":"First argument to `onLog` must be null or a function.","idb-open":"Error thrown when opening IndexedDB. Original error: {$originalErrorMessage}.","idb-get":"Error thrown when reading from IndexedDB. Original error: {$originalErrorMessage}.","idb-set":"Error thrown when writing to IndexedDB. Original error: {$originalErrorMessage}.","idb-delete":"Error thrown when deleting from IndexedDB. Original error: {$originalErrorMessage}.","finalization-registry-not-supported":"FirebaseServerApp deleteOnDeref field defined but the JS runtime does not support FinalizationRegistry.","invalid-server-app-environment":"FirebaseServerApp is not for use in browser environments."},v=new I("app","Firebase",Dn);var ae=class{constructor(t,n,r){this._isDeleted=!1,this._options={...t},this._config={...n},this._name=n.name,this._automaticDataCollectionEnabled=n.automaticDataCollectionEnabled,this._container=r,this.container.addComponent(new m("app",()=>this,"PUBLIC"))}get automaticDataCollectionEnabled(){return this.checkDestroyed(),this._automaticDataCollectionEnabled}set automaticDataCollectionEnabled(t){this.checkDestroyed(),this._automaticDataCollectionEnabled=t}get name(){return this.checkDestroyed(),this._name}get options(){return this.checkDestroyed(),this._options}get config(){return this.checkDestroyed(),this._config}get container(){return this._container}get isDeleted(){return this._isDeleted}set isDeleted(t){this._isDeleted=t}checkDestroyed(){if(this.isDeleted)throw v.create("app-deleted",{appName:this._name})}};function Tn(e,t={}){let n=e;typeof t!="object"&&(t={name:t});let r={name:An,automaticDataCollectionEnabled:!0,...t},i=r.name;if(typeof i!="string"||!i)throw v.create("bad-app-name",{appName:String(i)});if(n||(n=xe()),!n)throw v.create("no-options");let s=ie.get(i);if(s)if(O(n,s.options)){if(O(r,s.config))return s;throw v.create("duplicate-app",{appName:i,mismatchedParam:"config",oldValue:JSON.stringify(s.config),newValue:JSON.stringify(r)})}else throw v.create("duplicate-app",{appName:i,mismatchedParam:"options",oldValue:JSON.stringify(s.options),newValue:JSON.stringify(n)});let a=new $(i);for(let c of se.values())a.addComponent(c);let o=new ae(n,r,a);return ie.set(i,o),o}function y(e,t,n){var a;let r=(a=Sn[e])!=null?a:e;n&&(r+=`-${n}`);let i=r.match(/\s|\//),s=t.match(/\s|\//);if(i||s){let o=[`Unable to register library "${r}" with version "${t}":`];i&&o.push(`library name "${r}" contains illegal characters (whitespace or "/")`),i&&s&&o.push("and"),s&&o.push(`version name "${t}" contains illegal characters (whitespace or "/")`),_.warn(o.join(" "));return}E(new m(`${r}-version`,()=>({library:r,version:t}),"VERSION"))}var On="firebase-heartbeat-database",xn=1,B="firebase-heartbeat-store",te=null;function Ve(){return te||(te=F(On,xn,{upgrade:(e,t)=>{switch(t){case 0:try{e.createObjectStore(B)}catch(n){console.warn(n)}}}}).catch(e=>{throw v.create("idb-open",{originalErrorMessage:e.message})})),te}async function kn(e){try{let n=(await Ve()).transaction(B),r=await n.objectStore(B).get(ze(e));return await n.done,r}catch(t){if(t instanceof b)_.warn(t.message);else{let n=v.create("idb-get",{originalErrorMessage:t==null?void 0:t.message});_.warn(n.message)}}}async function Fe(e,t){try{let r=(await Ve()).transaction(B,"readwrite");await r.objectStore(B).put(t,ze(e)),await r.done}catch(n){if(n instanceof b)_.warn(n.message);else{let r=v.create("idb-set",{originalErrorMessage:n==null?void 0:n.message});_.warn(r.message)}}}function ze(e){return`${e.name}!${e.options.appId}`}var Rn=1024,Nn=30,oe=class{constructor(t){this.container=t,this._heartbeatsCache=null;let n=this.container.getProvider("app").getImmediate();this._storage=new ce(n),this._heartbeatsCachePromise=this._storage.read().then(r=>(this._heartbeatsCache=r,r))}async triggerHeartbeat(){var t,n;try{let i=this.container.getProvider("platform-logger").getImmediate().getPlatformInfoString(),s=He();if(((t=this._heartbeatsCache)==null?void 0:t.heartbeats)==null&&(this._heartbeatsCache=await this._heartbeatsCachePromise,((n=this._heartbeatsCache)==null?void 0:n.heartbeats)==null)||this._heartbeatsCache.lastSentHeartbeatDate===s||this._heartbeatsCache.heartbeats.some(a=>a.date===s))return;if(this._heartbeatsCache.heartbeats.push({date:s,agent:i}),this._heartbeatsCache.heartbeats.length>Nn){let a=Pn(this._heartbeatsCache.heartbeats);this._heartbeatsCache.heartbeats.splice(a,1)}return this._storage.overwrite(this._heartbeatsCache)}catch(r){_.warn(r)}}async getHeartbeatsHeader(){var t;try{if(this._heartbeatsCache===null&&await this._heartbeatsCachePromise,((t=this._heartbeatsCache)==null?void 0:t.heartbeats)==null||this._heartbeatsCache.heartbeats.length===0)return"";let n=He(),{heartbeatsToSend:r,unsentEntries:i}=Bn(this._heartbeatsCache.heartbeats),s=j(JSON.stringify({version:2,heartbeats:r}));return this._heartbeatsCache.lastSentHeartbeatDate=n,i.length>0?(this._heartbeatsCache.heartbeats=i,await this._storage.overwrite(this._heartbeatsCache)):(this._heartbeatsCache.heartbeats=[],this._storage.overwrite(this._heartbeatsCache)),s}catch(n){return _.warn(n),""}}};function He(){return new Date().toISOString().substring(0,10)}function Bn(e,t=Rn){let n=[],r=e.slice();for(let i of e){let s=n.find(a=>a.agent===i.agent);if(s){if(s.dates.push(i.date),Ue(n)>t){s.dates.pop();break}}else if(n.push({agent:i.agent,dates:[i.date]}),Ue(n)>t){n.pop();break}r=r.slice(1)}return{heartbeatsToSend:n,unsentEntries:r}}var ce=class{constructor(t){this.app=t,this._canUseIndexedDBPromise=this.runIndexedDBEnvironmentCheck()}async runIndexedDBEnvironmentCheck(){return R()?N().then(()=>!0).catch(()=>!1):!1}async read(){if(await this._canUseIndexedDBPromise){let n=await kn(this.app);return n!=null&&n.heartbeats?n:{heartbeats:[]}}else return{heartbeats:[]}}async overwrite(t){var r;if(await this._canUseIndexedDBPromise){let i=await this.read();return Fe(this.app,{lastSentHeartbeatDate:(r=t.lastSentHeartbeatDate)!=null?r:i.lastSentHeartbeatDate,heartbeats:t.heartbeats})}else return}async add(t){var r;if(await this._canUseIndexedDBPromise){let i=await this.read();return Fe(this.app,{lastSentHeartbeatDate:(r=t.lastSentHeartbeatDate)!=null?r:i.lastSentHeartbeatDate,heartbeats:[...i.heartbeats,...t.heartbeats]})}else return}};function Ue(e){return j(JSON.stringify({version:2,heartbeats:e})).length}function Pn(e){if(e.length===0)return-1;let t=0,n=e[0].date;for(let r=1;r<e.length;r++)e[r].date<n&&(n=e[r].date,t=r);return t}function Mn(e){E(new m("platform-logger",t=>new ne(t),"PRIVATE")),E(new m("heartbeat",t=>new oe(t),"PRIVATE")),y(re,$e,e),y(re,$e,"esm2020"),y("fire-js","")}Mn("");var $n="firebase",Ln="12.19.0";y($n,Ln,"app");var qe="@firebase/installations",de="0.6.24";var Ge=1e4,Ke=`w:${de}`,Je="FIS_v2",Hn="https://firebaseinstallations.googleapis.com/v1",Un=3600*1e3,Vn="installations",zn="Installations";var jn={"missing-app-config-values":'Missing App configuration value: "{$valueName}"',"not-registered":"Firebase Installation is not registered.","installation-not-found":"Firebase Installation not found.","request-failed":'{$requestName} request failed with error "{$serverCode} {$serverStatus}: {$serverMessage}"',"app-offline":"Could not process request. Application offline.","delete-pending-registration":"Can't delete installation while there is a pending registration request."},D=new I(Vn,zn,jn);function Ye(e){return e instanceof b&&e.code.includes("request-failed")}function Xe({projectId:e}){return`${Hn}/projects/${e}/installations`}function Qe(e){return{token:e.token,requestStatus:2,expiresIn:qn(e.expiresIn),creationTime:Date.now()}}async function Ze(e,t){let r=(await t.json()).error;return D.create("request-failed",{requestName:e,serverCode:r.code,serverMessage:r.message,serverStatus:r.status})}function et({apiKey:e}){return new Headers({"Content-Type":"application/json",Accept:"application/json","x-goog-api-key":e})}function Wn(e,{refreshToken:t}){let n=et(e);return n.append("Authorization",Gn(t)),n}async function tt(e){let t=await e();return t.status>=500&&t.status<600?e():t}function qn(e){return Number(e.replace("s","000"))}function Gn(e){return`${Je} ${e}`}async function Kn({appConfig:e,heartbeatServiceProvider:t},{fid:n}){let r=Xe(e),i=et(e),s=t.getImmediate({optional:!0});if(s){let l=await s.getHeartbeatsHeader();l&&i.append("x-firebase-client",l)}let a={fid:n,authVersion:Je,appId:e.appId,sdkVersion:Ke},o={method:"POST",headers:i,body:JSON.stringify(a)},c=await tt(()=>fetch(r,o));if(c.ok){let l=await c.json();return{fid:l.fid||n,registrationStatus:2,refreshToken:l.refreshToken,authToken:Qe(l.authToken)}}else throw await Ze("Create Installation",c)}function nt(e){return new Promise(t=>{setTimeout(t,e)})}function Jn(e){return btoa(String.fromCharCode(...e)).replace(/\+/g,"-").replace(/\//g,"_")}var Yn=/^[cdef][\w-]{21}$/,ue="";function Xn(){try{let e=new Uint8Array(17);(self.crypto||self.msCrypto).getRandomValues(e),e[0]=112+e[0]%16;let n=Qn(e);return Yn.test(n)?n:ue}catch{return ue}}function Qn(e){return Jn(e).substr(0,22)}function U(e){return`${e.appName}!${e.appId}`}var rt=new Map;function it(e,t){let n=U(e);st(n,t),Zn(n,t)}function st(e,t){let n=rt.get(e);if(n)for(let r of n)r(t)}function Zn(e,t){let n=er();n&&n.postMessage({key:e,fid:t}),tr()}var C=null;function er(){return!C&&"BroadcastChannel"in self&&(C=new BroadcastChannel("[Firebase] FID Change"),C.onmessage=e=>{st(e.data.key,e.data.fid)}),C}function tr(){rt.size===0&&C&&(C.close(),C=null)}var nr="firebase-installations-database",rr=1,T="firebase-installations-store",le=null;function he(){return le||(le=F(nr,rr,{upgrade:(e,t)=>{switch(t){case 0:e.createObjectStore(T)}}})),le}async function H(e,t){let n=U(e),i=(await he()).transaction(T,"readwrite"),s=i.objectStore(T),a=await s.get(n);return await s.put(t,n),await i.done,(!a||a.fid!==t.fid)&&it(e,t.fid),t}async function at(e){let t=U(e),r=(await he()).transaction(T,"readwrite");await r.objectStore(T).delete(t),await r.done}async function V(e,t){let n=U(e),i=(await he()).transaction(T,"readwrite"),s=i.objectStore(T),a=await s.get(n),o=t(a);return o===void 0?await s.delete(n):await s.put(o,n),await i.done,o&&(!a||a.fid!==o.fid)&&it(e,o.fid),o}async function pe(e){let t,n=await V(e.appConfig,r=>{let i=ir(r),s=sr(e,i);return t=s.registrationPromise,s.installationEntry});return n.fid===ue?{installationEntry:await t}:{installationEntry:n,registrationPromise:t}}function ir(e){let t=e||{fid:Xn(),registrationStatus:0};return ot(t)}function sr(e,t){if(t.registrationStatus===0){if(!navigator.onLine){let i=Promise.reject(D.create("app-offline"));return{installationEntry:t,registrationPromise:i}}let n={fid:t.fid,registrationStatus:1,registrationTime:Date.now()},r=ar(e,n);return{installationEntry:n,registrationPromise:r}}else return t.registrationStatus===1?{installationEntry:t,registrationPromise:or(e)}:{installationEntry:t}}async function ar(e,t){try{let n=await Kn(e,t);return H(e.appConfig,n)}catch(n){throw Ye(n)&&n.customData.serverCode===409?await at(e.appConfig):await H(e.appConfig,{fid:t.fid,registrationStatus:0}),n}}async function or(e){let t=await je(e.appConfig);for(;t.registrationStatus===1;)await nt(100),t=await je(e.appConfig);if(t.registrationStatus===0){let{installationEntry:n,registrationPromise:r}=await pe(e);return r||n}return t}function je(e){return V(e,t=>{if(!t)throw D.create("installation-not-found");return ot(t)})}function ot(e){return cr(e)?{fid:e.fid,registrationStatus:0}:e}function cr(e){return e.registrationStatus===1&&e.registrationTime+Ge<Date.now()}async function lr({appConfig:e,heartbeatServiceProvider:t},n){let r=fr(e,n),i=Wn(e,n),s=t.getImmediate({optional:!0});if(s){let l=await s.getHeartbeatsHeader();l&&i.append("x-firebase-client",l)}let a={installation:{sdkVersion:Ke,appId:e.appId}},o={method:"POST",headers:i,body:JSON.stringify(a)},c=await tt(()=>fetch(r,o));if(c.ok){let l=await c.json();return Qe(l)}else throw await Ze("Generate Auth Token",c)}function fr(e,{fid:t}){return`${Xe(e)}/${t}/authTokens:generate`}async function me(e,t=!1){let n,r=await V(e.appConfig,s=>{if(!ct(s))throw D.create("not-registered");let a=s.authToken;if(!t&&hr(a))return s;if(a.requestStatus===1)return n=ur(e,t),s;{if(!navigator.onLine)throw D.create("app-offline");let o=mr(s);return n=dr(e,o),o}});return n?await n:r.authToken}async function ur(e,t){let n=await We(e.appConfig);for(;n.authToken.requestStatus===1;)await nt(100),n=await We(e.appConfig);let r=n.authToken;return r.requestStatus===0?me(e,t):r}function We(e){return V(e,t=>{if(!ct(t))throw D.create("not-registered");let n=t.authToken;return gr(n)?{...t,authToken:{requestStatus:0}}:t})}async function dr(e,t){try{let n=await lr(e,t),r={...t,authToken:n};return await H(e.appConfig,r),n}catch(n){if(Ye(n)&&(n.customData.serverCode===401||n.customData.serverCode===404))await at(e.appConfig);else{let r={...t,authToken:{requestStatus:0}};await H(e.appConfig,r)}throw n}}function ct(e){return e!==void 0&&e.registrationStatus===2}function hr(e){return e.requestStatus===2&&!pr(e)}function pr(e){let t=Date.now();return t<e.creationTime||e.creationTime+e.expiresIn<t+Un}function mr(e){let t={requestStatus:1,requestTime:Date.now()};return{...e,authToken:t}}function gr(e){return e.requestStatus===1&&e.requestTime+Ge<Date.now()}async function br(e){let t=e,{installationEntry:n,registrationPromise:r}=await pe(t);return r?r.catch(console.error):me(t).catch(console.error),n.fid}async function yr(e,t=!1){let n=e;return await wr(n),(await me(n,t)).token}async function wr(e){let{registrationPromise:t}=await pe(e);t&&await t}function Ir(e){if(!e||!e.options)throw fe("App Configuration");if(!e.name)throw fe("App Name");let t=["projectId","apiKey","appId"];for(let n of t)if(!e.options[n])throw fe(n);return{appName:e.name,projectId:e.options.projectId,apiKey:e.options.apiKey,appId:e.options.appId}}function fe(e){return D.create("missing-app-config-values",{valueName:e})}var lt="installations",_r="installations-internal",Er=e=>{let t=e.getProvider("app").getImmediate(),n=Ir(t),r=P(t,"heartbeat");return{app:t,appConfig:n,heartbeatServiceProvider:r,_delete:()=>Promise.resolve()}},vr=e=>{let t=e.getProvider("app").getImmediate(),n=P(t,lt).getImmediate();return{getId:()=>br(n),getToken:i=>yr(n,i)}};function Ar(){E(new m(lt,Er,"PUBLIC")),E(new m(_r,vr,"PRIVATE"))}Ar();y(qe,de);y(qe,de,"esm2020");var be="analytics",Sr="firebase_id",Cr="origin",Dr=60*1e3,Tr="https://firebase.googleapis.com/v1alpha/projects/-/apps/{app-id}/webConfig",ve="https://www.googletagmanager.com/gtag/js";var d=new x("@firebase/analytics");var Or={"already-exists":"A Firebase Analytics instance with the appId {$id}  already exists. Only one Firebase Analytics instance can be created for each appId.","already-initialized":"initializeAnalytics() cannot be called again with different options than those it was initially called with. It can be called again with the same options to return the existing instance, or getAnalytics() can be used to get a reference to the already-initialized instance.","already-initialized-settings":"Firebase Analytics has already been initialized.settings() must be called before initializing any Analytics instanceor it will have no effect.","interop-component-reg-failed":"Firebase Analytics Interop Component failed to instantiate: {$reason}","invalid-analytics-context":"Firebase Analytics is not supported in this environment. Wrap initialization of analytics in analytics.isSupported() to prevent initialization in unsupported environments. Details: {$errorInfo}","indexeddb-unavailable":"IndexedDB unavailable or restricted in this environment. Wrap initialization of analytics in analytics.isSupported() to prevent initialization in unsupported environments. Details: {$errorInfo}","fetch-throttle":"The config fetch request timed out while in an exponential backoff state. Unix timestamp in milliseconds when fetch request throttling ends: {$throttleEndTimeMillis}.","config-fetch-failed":"Dynamic config fetch failed: [{$httpStatus}] {$responseMessage}","no-api-key":'The "apiKey" field is empty in the local Firebase config. Firebase Analytics requires this field tocontain a valid API key.',"no-app-id":'The "appId" field is empty in the local Firebase config. Firebase Analytics requires this field tocontain a valid app ID.',"no-client-id":'The "client_id" field is empty.',"invalid-gtag-resource":"Trusted Types detected an invalid gtag resource: {$gtagURL}."},g=new I("analytics","Analytics",Or);function xr(e){if(!e.startsWith(ve)){let t=g.create("invalid-gtag-resource",{gtagURL:e});return d.warn(t.message),""}return e}function gt(e){return Promise.all(e.map(t=>t.catch(n=>n)))}function kr(e,t){let n;return window.trustedTypes&&(n=window.trustedTypes.createPolicy(e,t)),n}function Rr(e,t){let n=kr("firebase-js-sdk-policy",{createScriptURL:xr}),r=document.createElement("script"),i=`${ve}?l=${e}&id=${t}`;r.src=n?n==null?void 0:n.createScriptURL(i):i,r.async=!0,document.head.appendChild(r)}function Nr(e){let t=[];return Array.isArray(window[e])?t=window[e]:window[e]=t,t}async function Br(e,t,n,r,i,s){let a=r[i];try{if(a)await t[a];else{let c=(await gt(n)).find(l=>l.measurementId===i);c&&await t[c.appId]}}catch(o){d.error(o)}e("config",i,s)}async function Pr(e,t,n,r,i){try{let s=[];if(i&&i.send_to){let a=i.send_to;Array.isArray(a)||(a=[a]);let o=await gt(n);for(let c of a){let l=o.find(u=>u.measurementId===c),h=l&&t[l.appId];if(h)s.push(h);else{s=[];break}}}s.length===0&&(s=Object.values(t)),await Promise.all(s),e("event",r,i||{})}catch(s){d.error(s)}}function Mr(e,t,n,r){async function i(s,...a){try{if(s==="event"){let[o,c]=a;await Pr(e,t,n,o,c)}else if(s==="config"){let[o,c]=a;await Br(e,t,n,r,o,c)}else if(s==="consent"){let[o,c]=a;e("consent",o,c)}else if(s==="get"){let[o,c,l]=a;e("get",o,c,l)}else if(s==="set"){let[o]=a;e("set",o)}else e(s,...a)}catch(o){d.error(o)}}return i}function $r(e,t,n,r,i){let s=function(...a){window[r].push(arguments)};return window[i]&&typeof window[i]=="function"&&(s=window[i]),window[i]=Mr(s,e,t,n),{gtagCore:s,wrappedGtag:window[i]}}function Lr(e){let t=window.document.getElementsByTagName("script");for(let n of Object.values(t))if(n.src&&n.src.includes(ve)&&n.src.includes(e))return n;return null}var Fr=30,Hr=1e3,ye=class{constructor(t={},n=Hr){this.throttleMetadata=t,this.intervalMillis=n}getThrottleMetadata(t){return this.throttleMetadata[t]}setThrottleMetadata(t,n){this.throttleMetadata[t]=n}deleteThrottleMetadata(t){delete this.throttleMetadata[t]}},bt=new ye;function Ur(e){return new Headers({Accept:"application/json","x-goog-api-key":e})}async function Vr(e){var a;let{appId:t,apiKey:n}=e,r={method:"GET",headers:Ur(n)},i=Tr.replace("{app-id}",t),s=await fetch(i,r);if(s.status!==200&&s.status!==304){let o="";try{let c=await s.json();(a=c.error)!=null&&a.message&&(o=c.error.message)}catch{}throw g.create("config-fetch-failed",{httpStatus:s.status,responseMessage:o})}return s.json()}async function zr(e,t=bt,n){let{appId:r,apiKey:i,measurementId:s}=e.options;if(!r)throw g.create("no-app-id");if(!i){if(s)return{measurementId:s,appId:r};throw g.create("no-api-key")}let a=t.getThrottleMetadata(r)||{backoffCount:0,throttleEndTimeMillis:Date.now()},o=new we;return setTimeout(async()=>{o.abort()},Dr),yt({appId:r,apiKey:i,measurementId:s},a,o,t)}async function yt(e,{throttleEndTimeMillis:t,backoffCount:n},r,i=bt){var o;let{appId:s,measurementId:a}=e;try{await jr(r,t)}catch(c){if(a)return d.warn(`Timed out fetching this Firebase app's measurement ID from the server. Falling back to the measurement ID ${a} provided in the "measurementId" field in the local Firebase config. [${c==null?void 0:c.message}]`),{appId:s,measurementId:a};throw c}try{let c=await Vr(e);return i.deleteThrottleMetadata(s),c}catch(c){let l=c;if(!Wr(l)){if(i.deleteThrottleMetadata(s),a)return d.warn(`Failed to fetch this Firebase app's measurement ID from the server. Falling back to the measurement ID ${a} provided in the "measurementId" field in the local Firebase config. [${l==null?void 0:l.message}]`),{appId:s,measurementId:a};throw c}let h=Number((o=l==null?void 0:l.customData)==null?void 0:o.httpStatus)===503?G(n,i.intervalMillis,Fr):G(n,i.intervalMillis),u={throttleEndTimeMillis:Date.now()+h,backoffCount:n+1};return i.setThrottleMetadata(s,u),d.debug(`Calling attemptFetch again in ${h} millis`),yt(e,u,r,i)}}function jr(e,t){return new Promise((n,r)=>{let i=Math.max(t-Date.now(),0),s=setTimeout(n,i);e.addEventListener(()=>{clearTimeout(s),r(g.create("fetch-throttle",{throttleEndTimeMillis:t}))})})}function Wr(e){if(!(e instanceof b)||!e.customData)return!1;let t=Number(e.customData.httpStatus);return t===429||t===500||t===503||t===504}var we=class{constructor(){this.listeners=[]}addEventListener(t){this.listeners.push(t)}abort(){this.listeners.forEach(t=>t())}};var Ie;async function qr(e,t,n,r,i){if(i&&i.global){e("event",n,r);return}else{let s=await t,a={...r,send_to:s};e("event",n,a)}}async function Gr(e,t,n,r){if(r&&r.global){let i={};for(let s of Object.keys(n))i[`user_properties.${s}`]=n[s];return e("set",i),Promise.resolve()}else{let i=await t;e("config",i,{update:!0,user_properties:n})}}var _e;function Kr(e){_e=e}function Jr(e){Ie=e}async function Yr(){if(R())try{await N()}catch(e){return d.warn(g.create("indexeddb-unavailable",{errorInfo:e==null?void 0:e.toString()}).message),!1}else return d.warn(g.create("indexeddb-unavailable",{errorInfo:"IndexedDB is not available in this environment."}).message),!1;return!0}async function Xr(e,t,n,r,i,s,a){var A;let o=zr(e);o.then(p=>{n[p.measurementId]=p.appId,e.options.measurementId&&p.measurementId!==e.options.measurementId&&d.warn(`The measurement ID in the local Firebase config (${e.options.measurementId}) does not match the measurement ID fetched from the server (${p.measurementId}). To ensure analytics events are always sent to the correct Analytics property, update the measurement ID field in the local config or remove it from the local config.`)}).catch(p=>d.error(p)),t.push(o);let c=Yr().then(p=>{if(p)return r.getId()}),[l,h]=await Promise.all([o,c]);Lr(s)||Rr(s,l.measurementId),_e&&(i("consent","default",_e),Kr(void 0)),i("js",new Date);let u=(A=a==null?void 0:a.config)!=null?A:{};return u[Cr]="firebase",u.update=!0,h!=null&&(u[Sr]=h),i("config",l.measurementId,u),Ie&&(i("set",Ie),Jr(void 0)),l.measurementId}var Ee=class{constructor(t){this.app=t}_delete(){return delete k[this.app.options.appId],Promise.resolve()}},k={},ft=[],ut={},ge="dataLayer",Qr="gtag",dt,Ae,ht=!1;function Zr(){let e=[];if(W()&&e.push("This is a browser extension environment."),q()||e.push("Cookies are not available."),e.length>0){let t=e.map((r,i)=>`(${i+1}) ${r}`).join(" "),n=g.create("invalid-analytics-context",{errorInfo:t});d.warn(n.message)}}function ei(e,t,n){Zr();let r=e.options.appId;if(!r)throw g.create("no-app-id");if(!e.options.apiKey)if(e.options.measurementId)d.warn(`The "apiKey" field is empty in the local Firebase config. This is needed to fetch the latest measurement ID for this Firebase app. Falling back to the measurement ID ${e.options.measurementId} provided in the "measurementId" field in the local Firebase config.`);else throw g.create("no-api-key");if(k[r]!=null)throw g.create("already-exists",{id:r});if(!ht){Nr(ge);let{wrappedGtag:s,gtagCore:a}=$r(k,ft,ut,ge,Qr);Ae=s,dt=a,ht=!0}return k[r]=Xr(e,ft,ut,t,dt,ge,n),new Ee(e)}function ti(e,t={}){let n=P(e,be);if(n.isInitialized()){let i=n.getImmediate();if(O(t,n.getOptions()))return i;throw g.create("already-initialized")}return n.initialize({options:t})}async function ni(){if(W()||!q()||!R())return!1;try{return await N()}catch{return!1}}function ri(e,t,n){e=K(e),Gr(Ae,k[e.app.options.appId],t,n).catch(r=>d.error(r))}function wt(e,t,n,r){e=K(e),qr(Ae,k[e.app.options.appId],t,n,r).catch(i=>d.error(i))}var pt="@firebase/analytics",mt="0.10.25";function ii(){E(new m(be,(t,{options:n})=>{let r=t.getProvider("app").getImmediate(),i=t.getProvider("installations-internal").getImmediate();return ei(r,i,n)},"PUBLIC")),E(new m("analytics-internal",e,"PRIVATE")),y(pt,mt),y(pt,mt,"esm2020");function e(t){try{let n=t.getProvider(be).getImmediate();return{logEvent:(r,i,s)=>wt(n,r,i,s),setUserProperties:(r,i)=>ri(n,r,i)}}catch(n){throw g.create("interop-component-reg-failed",{reason:n})}}}ii();export{ti as initializeAnalytics,Tn as initializeApp,ni as isSupported,wt as logEvent};
/*! Bundled license information:

@firebase/util/dist/index.esm.js:
@firebase/util/dist/index.esm.js:
@firebase/util/dist/index.esm.js:
@firebase/util/dist/index.esm.js:
@firebase/util/dist/index.esm.js:
@firebase/util/dist/index.esm.js:
@firebase/util/dist/index.esm.js:
@firebase/util/dist/index.esm.js:
@firebase/util/dist/index.esm.js:
@firebase/util/dist/index.esm.js:
@firebase/util/dist/index.esm.js:
@firebase/logger/dist/esm/index.esm.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/util/dist/index.esm.js:
@firebase/util/dist/index.esm.js:
  (**
   * @license
   * Copyright 2022 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/util/dist/index.esm.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)
  (**
   * @license
   * Copyright 2021 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/util/dist/index.esm.js:
@firebase/installations/dist/esm/index.esm.js:
@firebase/analytics/dist/esm/index.esm.js:
  (**
   * @license
   * Copyright 2019 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)
  (**
   * @license
   * Copyright 2020 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/util/dist/index.esm.js:
  (**
   * @license
   * Copyright 2021 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)
  (**
   * @license
   * Copyright 2025 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/util/dist/index.esm.js:
  (**
   * @license
   * Copyright 2025 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/component/dist/esm/index.esm.js:
@firebase/app/dist/esm/index.esm.js:
@firebase/app/dist/esm/index.esm.js:
@firebase/app/dist/esm/index.esm.js:
@firebase/installations/dist/esm/index.esm.js:
@firebase/installations/dist/esm/index.esm.js:
@firebase/installations/dist/esm/index.esm.js:
@firebase/installations/dist/esm/index.esm.js:
@firebase/analytics/dist/esm/index.esm.js:
  (**
   * @license
   * Copyright 2019 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/app/dist/esm/index.esm.js:
  (**
   * @license
   * Copyright 2019 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)
  (**
   * @license
   * Copyright 2023 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/app/dist/esm/index.esm.js:
  (**
   * @license
   * Copyright 2021 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)
  (**
   * @license
   * Copyright 2019 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

firebase/app/dist/esm/index.esm.js:
@firebase/installations/dist/esm/index.esm.js:
@firebase/analytics/dist/esm/index.esm.js:
  (**
   * @license
   * Copyright 2020 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/analytics/dist/esm/index.esm.js:
  (**
   * @license
   * Copyright 2020 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)
  (**
   * @license
   * Copyright 2019 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)
*/
