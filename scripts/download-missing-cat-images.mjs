import mysql from "mysql2/promise";
import fs from "node:fs/promises";
import path from "node:path";

const OUTPUT_DIRECTORY = path.join(
  process.cwd(),
  "public",
  "images",
  "animals"
);

const CAT_API_URL =
  "https://api.thecatapi.com/v1/images/search";

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

function extensionFromContentType(contentType = "") {
  const type = contentType.toLowerCase();

  if (type.includes("png")) return ".png";
  if (type.includes("webp")) return ".webp";
  if (type.includes("gif")) return ".gif";

  return ".jpg";
}

async function requestRandomCat(attempt = 1) {
  const requestUrl = new URL(CAT_API_URL);

  requestUrl.searchParams.set("limit", "1");
  requestUrl.searchParams.set("order", "RANDOM");
  requestUrl.searchParams.set("mime_types", "jpg,png");
  requestUrl.searchParams.set("size", "med");

  const response = await fetch(requestUrl, {
    headers: {
      "x-api-key":
        process.env.CAT_API_KEY || "DEMO-API-KEY",
      Accept: "application/json",
    },
  });

  if (response.status === 429 && attempt <= 5) {
    const waitTime = attempt * 5000;

    console.log(
      `Rate limited. Waiting ${waitTime / 1000} seconds...`
    );

    await delay(waitTime);

    return requestRandomCat(attempt + 1);
  }

  if (!response.ok) {
    throw new Error(
      `TheCatAPI returned HTTP ${response.status}`
    );
  }

  const data = await response.json();
  const image = data?.[0];

  if (!image?.url) {
    throw new Error("TheCatAPI did not return an image URL");
  }

  return {
    id: image.id,
    url: image.url,
  };
}

async function downloadImage(imageUrl, attempt = 1) {
  const response = await fetch(imageUrl, {
    redirect: "follow",
    headers: {
      "User-Agent":
        "PawConnectStudentProject/1.0",
      Accept: "image/*",
    },
  });

  if (
    (response.status === 429 ||
      response.status >= 500) &&
    attempt <= 5
  ) {
    const waitTime = attempt * 4000;

    console.log(
      `Image server busy. Retrying in ${
        waitTime / 1000
      } seconds...`
    );

    await delay(waitTime);

    return downloadImage(imageUrl, attempt + 1);
  }

  if (!response.ok) {
    throw new Error(
      `Image download returned HTTP ${response.status}`
    );
  }

  const contentType =
    response.headers.get("content-type") || "";

  if (!contentType.startsWith("image/")) {
    throw new Error(
      `Response was not an image: ${contentType}`
    );
  }

  const buffer = Buffer.from(
    await response.arrayBuffer()
  );

  return {
    buffer,
    extension:
      extensionFromContentType(contentType),
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

  let downloaded = 0;
  let skipped = 0;
  let failed = 0;

  const usedImageIds = new Set();

  try {
    const [animals] = await connection.execute(`
      SELECT id, name, breed, image_url
      FROM animals
      WHERE id BETWEEN 51 AND 100
      ORDER BY id ASC
    `);

    console.log(
      `Found ${animals.length} cat records.\n`
    );

    for (const animal of animals) {
      const currentImage =
        animal.image_url?.trim() || "";

      if (
        currentImage.startsWith(
          "/images/animals/"
        )
      ) {
        console.log(
          `Skipped ${animal.id}: ${animal.name} already has a local image`
        );

        skipped++;
        continue;
      }

      try {
        console.log(
          `Downloading ${animal.id}: ${animal.name}`
        );

        let selectedCat = null;

        for (let attempt = 1; attempt <= 10; attempt++) {
          const candidate =
            await requestRandomCat();

          if (!usedImageIds.has(candidate.id)) {
            selectedCat = candidate;
            break;
          }

          await delay(1000);
        }

        if (!selectedCat) {
          throw new Error(
            "Could not find a unique cat image"
          );
        }

        const { buffer, extension } =
          await downloadImage(selectedCat.url);

        const fileName = `${
          animal.id
        }-${slugify(animal.name)}${extension}`;

        const filePath = path.join(
          OUTPUT_DIRECTORY,
          fileName
        );

        const databasePath =
          `/images/animals/${fileName}`;

        await fs.writeFile(filePath, buffer);

        await connection.execute(
          `
            UPDATE animals
            SET image_url = ?
            WHERE id = ?
          `,
          [databasePath, animal.id]
        );

        usedImageIds.add(selectedCat.id);

        downloaded++;

        console.log(
          `Saved: ${databasePath}\n`
        );
      } catch (error) {
        failed++;

        console.error(
          `Failed ${animal.id} (${animal.name}): ${error.message}\n`
        );
      }

      // Avoid rapidly hammering the API.
      await delay(2500);
    }

    console.log("\nFinished.");
    console.log(`Downloaded: ${downloaded}`);
    console.log(`Already local: ${skipped}`);
    console.log(`Failed: ${failed}`);
  } finally {
    await connection.end();
  }
}

main().catch((error) => {
  console.error(
    "Image process failed:",
    error
  );

  process.exit(1);
});