import mysql from "mysql2/promise";
import fs from "node:fs/promises";
import path from "node:path";

const COMMONS_API =
  "https://commons.wikimedia.org/w/api.php";

const OUTPUT_DIRECTORY = path.join(
  process.cwd(),
  "public",
  "images",
  "animals"
);

const ATTRIBUTION_FILE = path.join(
  OUTPUT_DIRECTORY,
  "cat-image-attributions.json"
);

const delay = (milliseconds) =>
  new Promise((resolve) => setTimeout(resolve, milliseconds));

function slugify(value = "cat") {
  return value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 60);
}

function cleanHtml(value = "") {
  return value
    .replace(/<[^>]*>/g, "")
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&quot;/g, '"')
    .trim();
}

function extensionFromMime(mime = "") {
  const normalizedMime = mime.toLowerCase();

  if (normalizedMime.includes("png")) return ".png";
  if (normalizedMime.includes("webp")) return ".webp";
  if (normalizedMime.includes("gif")) return ".gif";

  return ".jpg";
}

function normalizeBreed(breed = "") {
  return breed
    .replace(/\bmixed breed\b/gi, "")
    .replace(/\bmix\b/gi, "")
    .replace(/\bcat\b/gi, "")
    .trim();
}

async function searchCommonsImages(searchTerm) {
  const parameters = new URLSearchParams({
    action: "query",
    format: "json",
    origin: "*",

    generator: "search",
    gsrsearch: `${searchTerm} cat`,
    gsrnamespace: "6",
    gsrlimit: "15",

    prop: "imageinfo",
    iiprop: "url|mime|extmetadata",
    iiurlwidth: "1000",
  });

  const response = await fetch(
    `${COMMONS_API}?${parameters.toString()}`,
    {
      headers: {
        "User-Agent":
          "PawConnectStudentProject/1.0",
      },
    }
  );

  if (!response.ok) {
    throw new Error(
      `Wikimedia API returned HTTP ${response.status}`
    );
  }

  const data = await response.json();

  if (data.error) {
    throw new Error(
      data.error.info || "Wikimedia API error"
    );
  }

  const pages = Object.values(data.query?.pages || {});

  return pages
    .map((page) => {
      const imageInfo = page.imageinfo?.[0];

      if (!imageInfo) {
        return null;
      }

      return {
        title: page.title,
        downloadUrl:
          imageInfo.thumburl || imageInfo.url,
        originalUrl: imageInfo.url,
        descriptionUrl:
          imageInfo.descriptionurl || "",
        mime: imageInfo.thumbmime || imageInfo.mime || "",
        metadata: imageInfo.extmetadata || {},
      };
    })
    .filter(Boolean)
    .filter((image) =>
      image.mime.startsWith("image/")
    );
}

async function findUniqueImage(
  animal,
  usedOriginalUrls
) {
  const breed = normalizeBreed(animal.breed);

  const searchTerms = [
    breed,
    `${breed} domestic`,
    "domestic cat portrait",
    "house cat",
  ].filter(Boolean);

  for (const searchTerm of searchTerms) {
    const results =
      await searchCommonsImages(searchTerm);

    const unusedImage = results.find(
      (image) =>
        image.downloadUrl &&
        image.originalUrl &&
        !usedOriginalUrls.has(image.originalUrl)
    );

    if (unusedImage) {
      return unusedImage;
    }

    await delay(300);
  }

  return null;
}

async function downloadImage(url) {
  const response = await fetch(url, {
    redirect: "follow",
    headers: {
      "User-Agent":
        "PawConnectStudentProject/1.0",
      Accept: "image/*",
    },
  });

  if (!response.ok) {
    throw new Error(
      `Image download returned HTTP ${response.status}`
    );
  }

  const contentType =
    response.headers.get("content-type") || "";

  if (!contentType.startsWith("image/")) {
    throw new Error(
      `Downloaded content is not an image: ${contentType}`
    );
  }

  const arrayBuffer = await response.arrayBuffer();

  return {
    buffer: Buffer.from(arrayBuffer),
    mime: contentType,
  };
}

async function main() {
  await fs.mkdir(OUTPUT_DIRECTORY, {
    recursive: true,
  });

  const connection = await mysql.createConnection({
    host: process.env.DB_HOST || "localhost",
    port: Number(process.env.DB_PORT || 3306),
    user: process.env.DB_USER || "root",
    password: process.env.DB_PASSWORD || "",
    database: process.env.DB_NAME || "pawconnect",
  });

  const usedOriginalUrls = new Set();
  const attributions = [];

  let downloaded = 0;
  let failed = 0;

  try {
    const [animals] = await connection.execute(`
      SELECT id, name, breed, type, image_url
      FROM animals
      WHERE id BETWEEN 51 AND 100
      ORDER BY id ASC
    `);

    console.log(
      `Found ${animals.length} cat records.\n`
    );

    for (const animal of animals) {
      try {
        console.log(
          `Searching ${animal.id}: ${animal.name} (${animal.breed || "cat"})`
        );

        const selectedImage = await findUniqueImage(
          animal,
          usedOriginalUrls
        );

        if (!selectedImage) {
          throw new Error(
            "No unused Wikimedia image was found"
          );
        }

        const { buffer, mime } =
          await downloadImage(
            selectedImage.downloadUrl
          );

        const extension =
          extensionFromMime(mime);

        const safeName =
          slugify(animal.name) || "cat";

        const fileName =
          `${animal.id}-${safeName}${extension}`;

        const localFilePath = path.join(
          OUTPUT_DIRECTORY,
          fileName
        );

        const databasePath =
          `/images/animals/${fileName}`;

        await fs.writeFile(localFilePath, buffer);

        await connection.execute(
          `
            UPDATE animals
            SET image_url = ?
            WHERE id = ?
          `,
          [databasePath, animal.id]
        );

        usedOriginalUrls.add(
          selectedImage.originalUrl
        );

        const metadata =
          selectedImage.metadata;

        attributions.push({
          animalId: animal.id,
          animalName: animal.name,
          breed: animal.breed,
          localFile: databasePath,
          commonsTitle: selectedImage.title,
          originalImageUrl:
            selectedImage.originalUrl,
          commonsPage:
            selectedImage.descriptionUrl,
          creator: cleanHtml(
            metadata.Artist?.value || "Unknown"
          ),
          license:
            metadata.LicenseShortName?.value ||
            metadata.License?.value ||
            "See Wikimedia Commons page",
          credit: cleanHtml(
            metadata.Credit?.value || ""
          ),
        });

        console.log(
          `Saved: ${databasePath}\n`
        );

        downloaded++;
      } catch (error) {
        failed++;

        console.error(
          `Failed ${animal.id} (${animal.name}): ${error.message}\n`
        );
      }

      // Be polite to Wikimedia's servers.
      await delay(600);
    }

    await fs.writeFile(
      ATTRIBUTION_FILE,
      JSON.stringify(attributions, null, 2),
      "utf8"
    );

    console.log("Finished.");
    console.log(`Downloaded: ${downloaded}`);
    console.log(`Failed: ${failed}`);
    console.log(
      `Attributions saved to: ${ATTRIBUTION_FILE}`
    );
  } finally {
    await connection.end();
  }
}

main().catch((error) => {
  console.error(
    "Cat image process failed:",
    error
  );

  process.exit(1);
});