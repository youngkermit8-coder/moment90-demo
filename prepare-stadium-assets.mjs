import {execFileSync} from 'node:child_process';
import {copyFile, mkdtemp, readFile, rm, writeFile} from 'node:fs/promises';
import {createRequire} from 'node:module';
import {tmpdir} from 'node:os';
import {dirname, join, resolve} from 'node:path';
import sharp from 'sharp';

const studio = resolve(process.argv[2] ?? 'public/studio');
const deps = createRequire(import.meta.url);
const cli = resolve('node_modules/.bin/gltf-transform');
const work = await mkdtemp(join(tmpdir(), 'moment90-stadium-'));

try {
  const source = join(studio, 'models/stadium-v3.glb');
  const textures = join(work, 'stadium-webp.glb');
  const compressed = join(studio, 'models/stadium-web-v1.glb');
  execFileSync(cli, ['webp', source, textures, '--quality', '90', '--slots', 'baseColorTexture'], {stdio: 'inherit'});
  execFileSync(cli, ['meshopt', textures, compressed, '--level', 'medium', '--quantize-position', '16', '--quantize-texcoord', '14'], {stdio: 'inherit'});

  const meshoptDir = dirname(deps.resolve('meshoptimizer/decoder'));
  await copyFile(join(meshoptDir, 'meshopt_decoder.mjs'), join(studio, 'lib/meshopt_decoder.mjs'));
  await copyFile(join(meshoptDir, 'LICENSE.md'), join(studio, 'lib/meshopt-LICENSE.md'));

  const arena = join(studio, 'bayern/assets/allianz-interactive');
  const data = JSON.parse(await readFile(join(arena, 'allianz.gltf'), 'utf8'));
  const buffers = await Promise.all(data.buffers.map(buffer => readFile(join(arena, buffer.uri))));
  const texturesByView = new Map(data.images.map(image => [image.bufferView, image]));
  const parts = buffers.map(() => []);
  const lengths = buffers.map(() => 0);

  // Repack each split buffer so the old texture bytes are no longer transferred.
  // Draco and the source mesh layout can be copied exactly.
  for (const [index, view] of data.bufferViews.entries()) {
    const group = view.buffer;
    const offset = view.byteOffset ?? 0;
    let bytes = buffers[group].subarray(offset, offset + view.byteLength);
    const image = texturesByView.get(index);
    if (image) {
      const texture = sharp(bytes).resize({width:1024, height:1024, fit:'inside', withoutEnlargement:true});
      bytes = image.mimeType === 'image/jpeg'
        ? await texture.jpeg({quality:90, chromaSubsampling:'4:4:4'}).toBuffer()
        : await texture.png().toBuffer();
    }
    const padding = (4 - lengths[group] % 4) % 4;
    if (padding) parts[group].push(Buffer.alloc(padding));
    view.byteOffset = lengths[group] + padding;
    view.byteLength = bytes.length;
    lengths[group] = view.byteOffset + view.byteLength;
    parts[group].push(bytes);
  }

  for (const [index, buffer] of data.buffers.entries()) {
    buffer.uri = 'web-v1-' + buffer.uri;
    buffer.byteLength = lengths[index];
    await writeFile(join(arena, buffer.uri), Buffer.concat(parts[index], buffer.byteLength));
  }
  await writeFile(join(arena, 'allianz-web-v1.gltf'), JSON.stringify(data));
  console.info('Allianz buffers:', buffers.reduce((total, buffer) => total + buffer.length, 0), '→', lengths.reduce((total, length) => total + length, 0), 'bytes');
} finally {
  await rm(work, {recursive:true, force:true});
}
