"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

const emptyAnimalForm = {
  name: "",
  type: "dog",
  breed: "",
  size: "Medium",
  age: "",
  gender: "Male",
  temperament: "",
  location: "",
  health_status: "Healthy",
  vaccination_status: "Fully Vaccinated",
  sterilization_status: "Sterilized",
  description: "",
  image_url: "",
  adoption_status: "available",
};

export default function ShelterPage() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [shelter, setShelter] = useState(null);

  const [animals, setAnimals] = useState([]);
  const [adoptionRequests, setAdoptionRequests] = useState([]);

  const [animalForm, setAnimalForm] = useState(emptyAnimalForm);
  const [editingAnimalId, setEditingAnimalId] = useState(null);

  const [loading, setLoading] = useState(true);
  const [savingAnimal, setSavingAnimal] = useState(false);

  const [message, setMessage] = useState("");
  const [messageType, setMessageType] = useState("success");

  useEffect(() => {
    const savedShelter = localStorage.getItem("shelter");

    if (!savedShelter) {
      window.location.href = "/shelter-login";
      return;
    }

    try {
      const parsedShelter = JSON.parse(savedShelter);

      if (!parsedShelter?.shelter_id) {
        throw new Error("Invalid shelter session.");
      }

      setShelter(parsedShelter);
      loadDashboardData(parsedShelter.shelter_id);
    } catch {
      localStorage.removeItem("shelter");
      window.location.href = "/shelter-login";
    }
  }, []);

  async function loadDashboardData(shelterId) {
    try {
      setLoading(true);

      const [animalsResponse, requestsResponse] = await Promise.all([
        fetch("/api/animals", {
          cache: "no-store",
        }),
        fetch(`/api/adoption-requests?shelter_id=${shelterId}`, {
          cache: "no-store",
        }),
      ]);

      const animalsData = await readJsonResponse(animalsResponse);
      const requestsData = await readJsonResponse(requestsResponse);

      if (!animalsResponse.ok) {
        throw new Error(
          animalsData.error || "Failed to load animal records."
        );
      }

      if (!requestsResponse.ok) {
        throw new Error(
          requestsData.error || "Failed to load adoption requests."
        );
      }

      const shelterAnimals = Array.isArray(animalsData)
        ? animalsData.filter(
            (animal) =>
              Number(animal.shelter_id) === Number(shelterId)
          )
        : [];

      setAnimals(shelterAnimals);

      setAdoptionRequests(
        Array.isArray(requestsData) ? requestsData : []
      );
    } catch (error) {
      showMessage(
        error.message || "Dashboard data could not be loaded.",
        "error"
      );
    } finally {
      setLoading(false);
    }
  }

  function showMessage(text, type = "success") {
    setMessage(text);
    setMessageType(type);

    window.setTimeout(() => {
      setMessage("");
    }, 3500);
  }

  function handleAnimalChange(event) {
    const { name, value } = event.target;

    setAnimalForm((current) => ({
      ...current,
      [name]: value,
    }));
  }

  function resetAnimalForm() {
    setAnimalForm(emptyAnimalForm);
    setEditingAnimalId(null);
  }

  function openAddAnimal() {
    resetAnimalForm();
    setActiveTab("addAnimal");

    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  }

  function handleEditAnimal(animal) {
    setEditingAnimalId(animal.id);

    setAnimalForm({
      name: animal.name || "",
      type: animal.type || "dog",
      breed: animal.breed || "",
      size: animal.size || "Medium",
      age: animal.age || "",
      gender: animal.gender || "Male",
      temperament: animal.temperament || "",
      location: animal.location || "",
      health_status: animal.health_status || "Healthy",
      vaccination_status:
        animal.vaccination_status || "Fully Vaccinated",
      sterilization_status:
        animal.sterilization_status || "Sterilized",
      description: animal.description || "",
      image_url: animal.image_url || "",
      adoption_status:
        animal.adoption_status || "available",
    });

    setActiveTab("addAnimal");

    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  }

  async function handleAnimalSubmit(event) {
    event.preventDefault();

    if (!shelter?.shelter_id) {
      showMessage("Shelter session could not be found.", "error");
      return;
    }

    try {
      setSavingAnimal(true);

      const method = editingAnimalId ? "PUT" : "POST";

      const payload = {
        ...animalForm,
        shelter_id: shelter.shelter_id,
      };

      if (editingAnimalId) {
        payload.id = editingAnimalId;
      }

      const response = await fetch("/api/animals", {
        method,
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      const data = await readJsonResponse(response);

      if (!response.ok) {
        throw new Error(
          data.error ||
            `Animal could not be ${
              editingAnimalId ? "updated" : "added"
            }.`
        );
      }

      showMessage(
        editingAnimalId
          ? "Animal updated successfully."
          : "Animal added successfully."
      );

      resetAnimalForm();

      await loadDashboardData(shelter.shelter_id);

      setActiveTab("animals");
    } catch (error) {
      showMessage(
        error.message || "Animal action failed.",
        "error"
      );
    } finally {
      setSavingAnimal(false);
    }
  }

  async function handleDeleteAnimal(id) {
    const confirmed = window.confirm(
      "Delete this animal record permanently?"
    );

    if (!confirmed) {
      return;
    }

    try {
      const response = await fetch("/api/animals", {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ id }),
      });

      const data = await readJsonResponse(response);

      if (!response.ok) {
        throw new Error(
          data.error || "Animal could not be deleted."
        );
      }

      showMessage("Animal deleted successfully.");

      await loadDashboardData(shelter.shelter_id);
    } catch (error) {
      showMessage(error.message || "Delete failed.", "error");
    }
  }

  async function updateAdoptionRequest(id, status) {
    const actionText =
      status === "approved" ? "approve" : "reject";

    const confirmed = window.confirm(
      `Are you sure you want to ${actionText} this application?`
    );

    if (!confirmed) {
      return;
    }

    try {
      const response = await fetch("/api/adoption-requests", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          id,
          status,
        }),
      });

      const data = await readJsonResponse(response);

      if (!response.ok) {
        throw new Error(
          data.error ||
            "Application status could not be updated."
        );
      }

      showMessage(`Application ${status} successfully.`);

      await loadDashboardData(shelter.shelter_id);
    } catch (error) {
      showMessage(
        error.message || "Application update failed.",
        "error"
      );
    }
  }

  function handleLogout() {
    localStorage.removeItem("shelter");
    window.location.href = "/shelter-login";
  }

  const availableAnimals = useMemo(() => {
    return animals.filter(
      (animal) =>
        animal.adoption_status?.toLowerCase() === "available"
    );
  }, [animals]);

  const adoptedAnimals = useMemo(() => {
    return animals.filter(
      (animal) =>
        animal.adoption_status?.toLowerCase() === "adopted"
    );
  }, [animals]);

  const pendingRequests = useMemo(() => {
    return adoptionRequests.filter(
      (request) =>
        request.status?.toLowerCase() === "pending"
    );
  }, [adoptionRequests]);

  return (
    <main className="min-h-screen bg-slate-100 text-slate-900 flex">
      <aside className="fixed left-0 top-0 bottom-0 w-72 bg-slate-950 text-white p-6 overflow-y-auto">
        <Link
          href="/"
          className="block text-2xl font-extrabold text-green-400 mb-2"
        >
          🐾 PawConnect
        </Link>

        <p className="text-sm text-slate-400 mb-8">
          Shelter Management
        </p>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 mb-8">
          <p className="text-xs uppercase tracking-wide text-slate-400 mb-1">
            Logged in as
          </p>

          <p className="font-extrabold">
            {shelter?.shelter_name || "Shelter"}
          </p>

          <p className="text-sm text-slate-400 mt-1">
            {shelter?.email || ""}
          </p>
        </div>

        <nav className="space-y-2">
          <SideItem
            icon="▦"
            label="Dashboard"
            tab="dashboard"
            activeTab={activeTab}
            setActiveTab={setActiveTab}
          />

          <SideItem
            icon="🐾"
            label="Animals"
            tab="animals"
            activeTab={activeTab}
            setActiveTab={setActiveTab}
          />

          <button
            type="button"
            onClick={openAddAnimal}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl font-bold ${
              activeTab === "addAnimal"
                ? "bg-green-700 text-white"
                : "text-slate-300 hover:bg-slate-900 hover:text-white"
            }`}
          >
            <span>+</span>
            <span>Add Animal</span>
          </button>

          <SideItem
            icon="📋"
            label="Adoption Requests"
            tab="adoptionRequests"
            activeTab={activeTab}
            setActiveTab={setActiveTab}
            badge={pendingRequests.length}
          />

          <Link
            href="/shelter-profile"
            className="w-full flex items-center gap-3 px-4 py-3 rounded-xl font-bold text-slate-300 hover:bg-slate-900 hover:text-white"
          >
            <span>🏠</span>
            <span>Shelter Profile</span>
          </Link>
        </nav>

        <div className="border-t border-slate-800 mt-8 pt-6">
          <button
            type="button"
            onClick={handleLogout}
            className="w-full text-left px-4 py-3 rounded-xl font-bold text-red-300 hover:bg-red-950 hover:text-red-200"
          >
            ↪ Logout
          </button>
        </div>
      </aside>

      <section className="flex-1 ml-72 p-8 lg:p-10">
        <div className="max-w-7xl mx-auto">
          <header className="flex flex-wrap items-start justify-between gap-5 mb-8">
            <div>
              <p className="text-green-700 font-bold mb-1">
                Shelter Workspace
              </p>

              <h1 className="text-4xl lg:text-5xl font-extrabold text-slate-950">
                {getPageTitle(activeTab, editingAnimalId)}
              </h1>

              <p className="text-slate-600 mt-2">
                {getPageDescription(activeTab)}
              </p>
            </div>

            <button
              type="button"
              onClick={openAddAnimal}
              className="bg-green-700 text-white px-6 py-3 rounded-xl font-bold hover:bg-green-800 shadow-sm"
            >
              + Add Animal
            </button>
          </header>

          {message && (
            <div
              className={`mb-6 border rounded-xl p-4 font-semibold ${
                messageType === "error"
                  ? "bg-red-100 border-red-300 text-red-800"
                  : "bg-green-100 border-green-300 text-green-800"
              }`}
            >
              {message}
            </div>
          )}

          {loading ? (
            <LoadingPanel />
          ) : (
            <>
              {activeTab === "dashboard" && (
                <DashboardContent
                  animals={animals}
                  availableAnimals={availableAnimals}
                  adoptedAnimals={adoptedAnimals}
                  pendingRequests={pendingRequests}
                  adoptionRequests={adoptionRequests}
                  setActiveTab={setActiveTab}
                  openAddAnimal={openAddAnimal}
                />
              )}

              {activeTab === "animals" && (
                <AnimalsContent
                  animals={animals}
                  onEdit={handleEditAnimal}
                  onDelete={handleDeleteAnimal}
                  openAddAnimal={openAddAnimal}
                />
              )}

              {activeTab === "addAnimal" && (
                <AnimalFormPanel
                  animalForm={animalForm}
                  editingAnimalId={editingAnimalId}
                  savingAnimal={savingAnimal}
                  onChange={handleAnimalChange}
                  onSubmit={handleAnimalSubmit}
                  onCancel={() => {
                    resetAnimalForm();
                    setActiveTab("animals");
                  }}
                />
              )}

              {activeTab === "adoptionRequests" && (
                <AdoptionRequestsContent
                  requests={adoptionRequests}
                  onUpdate={updateAdoptionRequest}
                />
              )}
            </>
          )}
        </div>
      </section>
    </main>
  );
}

function DashboardContent({
  animals,
  availableAnimals,
  adoptedAnimals,
  pendingRequests,
  adoptionRequests,
  setActiveTab,
  openAddAnimal,
}) {
  return (
    <>
      <div className="grid sm:grid-cols-2 xl:grid-cols-4 gap-5 mb-8">
        <StatCard
          label="Total Animals"
          value={animals.length}
          icon="🐾"
          note="All shelter records"
        />

        <StatCard
          label="Available Animals"
          value={availableAnimals.length}
          icon="🏡"
          note="Ready for adoption"
        />

        <StatCard
          label="Pending Requests"
          value={pendingRequests.length}
          icon="📋"
          note="Awaiting review"
        />

        <StatCard
          label="Successful Adoptions"
          value={adoptedAnimals.length}
          icon="✓"
          note="Animals adopted"
        />
      </div>

      <div className="grid xl:grid-cols-2 gap-6 mb-8">
        <Panel
          title="Recent Animals"
          action={
            <button
              type="button"
              onClick={() => setActiveTab("animals")}
              className="text-green-700 font-bold hover:underline"
            >
              View all
            </button>
          }
        >
          {animals.length === 0 ? (
            <EmptyState
              title="No animals added"
              text="Add your first animal record."
              buttonText="Add Animal"
              onClick={openAddAnimal}
            />
          ) : (
            <div className="space-y-3">
              {animals.slice(0, 5).map((animal) => (
                <RecentAnimalItem
                  key={animal.id}
                  animal={animal}
                />
              ))}
            </div>
          )}
        </Panel>

        <Panel
          title="Recent Adoption Requests"
          action={
            <button
              type="button"
              onClick={() => setActiveTab("adoptionRequests")}
              className="text-green-700 font-bold hover:underline"
            >
              Review requests
            </button>
          }
        >
          {adoptionRequests.length === 0 ? (
            <EmptyState
              title="No requests yet"
              text="New adoption applications will appear here."
            />
          ) : (
            <div className="space-y-3">
              {adoptionRequests.slice(0, 5).map((request) => (
                <RecentRequestItem
                  key={request.id}
                  request={request}
                />
              ))}
            </div>
          )}
        </Panel>
      </div>

      <Panel title="Quick Actions">
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <QuickAction
            title="Add New Animal"
            text="Create a public animal listing."
            icon="+"
            onClick={openAddAnimal}
          />

          <QuickAction
            title="Manage Animals"
            text="Edit animal and medical information."
            icon="🐾"
            onClick={() => setActiveTab("animals")}
          />

          <QuickAction
            title="Review Applications"
            text="Approve or reject adoption requests."
            icon="📋"
            onClick={() =>
              setActiveTab("adoptionRequests")
            }
          />
        </div>
      </Panel>
    </>
  );
}

function AnimalsContent({
  animals,
  onEdit,
  onDelete,
  openAddAnimal,
}) {
  const [search, setSearch] = useState("");

  const filteredAnimals = useMemo(() => {
    const keyword = search.toLowerCase().trim();

    if (!keyword) {
      return animals;
    }

    return animals.filter((animal) => {
      return (
        animal.name?.toLowerCase().includes(keyword) ||
        animal.type?.toLowerCase().includes(keyword) ||
        animal.breed?.toLowerCase().includes(keyword) ||
        animal.location?.toLowerCase().includes(keyword) ||
        animal.adoption_status
          ?.toLowerCase()
          .includes(keyword)
      );
    });
  }, [animals, search]);

  return (
    <Panel
      title="Animal Records"
      action={
        <button
          type="button"
          onClick={openAddAnimal}
          className="bg-green-700 text-white px-4 py-2 rounded-lg font-bold hover:bg-green-800"
        >
          + Add Animal
        </button>
      }
    >
      <input
        type="text"
        value={search}
        onChange={(event) => setSearch(event.target.value)}
        placeholder="Search by name, breed, location, or status..."
        className="w-full max-w-xl border border-slate-300 rounded-xl p-3 mb-6"
      />

      {filteredAnimals.length === 0 ? (
        <EmptyState
          title="No animal records found"
          text="Try another search or add a new animal."
          buttonText="Add Animal"
          onClick={openAddAnimal}
        />
      ) : (
        <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-5">
          {filteredAnimals.map((animal) => (
            <AnimalManagementCard
              key={animal.id}
              animal={animal}
              onEdit={onEdit}
              onDelete={onDelete}
            />
          ))}
        </div>
      )}
    </Panel>
  );
}

function AnimalFormPanel({
  animalForm,
  editingAnimalId,
  savingAnimal,
  onChange,
  onSubmit,
  onCancel,
}) {
  return (
    <Panel
      title={
        editingAnimalId
          ? `Edit ${animalForm.name || "Animal"}`
          : "Add New Animal"
      }
    >
      <form onSubmit={onSubmit} className="space-y-8">
        <FormSection
          title="Basic Information"
          description="Information shown on the public animal profile."
        >
          <div className="grid md:grid-cols-2 gap-5">
            <Input
              label="Animal Name"
              name="name"
              value={animalForm.name}
              onChange={onChange}
              placeholder="Example: Milo"
              required
            />

            <Select
              label="Animal Type"
              name="type"
              value={animalForm.type}
              onChange={onChange}
            >
              <option value="dog">Dog</option>
              <option value="cat">Cat</option>
              <option value="other">Other</option>
            </Select>

            <Input
              label="Breed"
              name="breed"
              value={animalForm.breed}
              onChange={onChange}
              placeholder="Example: Golden Retriever"
            />

            <Select
              label="Size"
              name="size"
              value={animalForm.size}
              onChange={onChange}
            >
              <option value="Small">Small</option>
              <option value="Medium">Medium</option>
              <option value="Large">Large</option>
              <option value="Extra Large">
                Extra Large
              </option>
              <option value="Unknown">Unknown</option>
            </Select>

            <Input
              label="Age"
              name="age"
              value={animalForm.age}
              onChange={onChange}
              placeholder="Example: 2 years"
              required
            />

            <Select
              label="Gender"
              name="gender"
              value={animalForm.gender}
              onChange={onChange}
            >
              <option value="Male">Male</option>
              <option value="Female">Female</option>
              <option value="Unknown">Unknown</option>
            </Select>

            <Input
              label="Temperament"
              name="temperament"
              value={animalForm.temperament}
              onChange={onChange}
              placeholder="Friendly, calm, playful..."
            />

            <Input
              label="Location"
              name="location"
              value={animalForm.location}
              onChange={onChange}
              placeholder="Rangsit, Pathum Thani"
              required
            />
          </div>
        </FormSection>

        <FormSection
          title="Medical and Adoption Information"
          description="Add health and adoption status details."
        >
          <div className="grid md:grid-cols-2 gap-5">
            <Input
              label="General Health"
              name="health_status"
              value={animalForm.health_status}
              onChange={onChange}
              placeholder="Healthy"
            />

            <Select
              label="Vaccination Status"
              name="vaccination_status"
              value={animalForm.vaccination_status}
              onChange={onChange}
            >
              <option value="Fully Vaccinated">
                Fully Vaccinated
              </option>
              <option value="Partially Vaccinated">
                Partially Vaccinated
              </option>
              <option value="Not Vaccinated">
                Not Vaccinated
              </option>
              <option value="Unknown">Unknown</option>
            </Select>

            <Select
              label="Sterilization Status"
              name="sterilization_status"
              value={animalForm.sterilization_status}
              onChange={onChange}
            >
              <option value="Sterilized">Sterilized</option>
              <option value="Not Sterilized">
                Not Sterilized
              </option>
              <option value="Unknown">Unknown</option>
            </Select>

            <Select
              label="Adoption Status"
              name="adoption_status"
              value={animalForm.adoption_status}
              onChange={onChange}
            >
              <option value="available">Available</option>
              <option value="pending">Pending</option>
              <option value="adopted">Adopted</option>
            </Select>
          </div>
        </FormSection>

        <FormSection
          title="Public Profile"
          description="Add a description and animal image."
        >
          <div className="space-y-5">
            <div>
              <label className="block mb-2 font-bold">
                About the Animal
              </label>

              <textarea
                name="description"
                value={animalForm.description}
                onChange={onChange}
                placeholder="Describe personality, background and ideal home..."
                className="w-full border border-slate-300 p-4 rounded-xl min-h-40"
              />
            </div>

            <Input
              label="Image URL"
              name="image_url"
              value={animalForm.image_url}
              onChange={onChange}
              placeholder="/images/milo.jpg"
            />
          </div>
        </FormSection>

        <div className="flex flex-wrap gap-3 border-t border-slate-200 pt-6">
          <button
            type="submit"
            disabled={savingAnimal}
            className="bg-green-700 text-white px-8 py-3 rounded-xl font-bold hover:bg-green-800 disabled:bg-slate-400"
          >
            {savingAnimal
              ? "Saving Animal..."
              : editingAnimalId
              ? "Update Animal"
              : "Add Animal"}
          </button>

          <button
            type="button"
            onClick={onCancel}
            className="border border-slate-300 px-8 py-3 rounded-xl font-bold hover:bg-slate-100"
          >
            Cancel
          </button>
        </div>
      </form>
    </Panel>
  );
}

function AdoptionRequestsContent({
  requests,
  onUpdate,
}) {
  const [filter, setFilter] = useState("all");

  const filteredRequests = useMemo(() => {
    if (filter === "all") {
      return requests;
    }

    return requests.filter(
      (request) =>
        request.status?.toLowerCase() === filter
    );
  }, [requests, filter]);

  return (
    <Panel title="Adoption Requests">
      <div className="flex flex-wrap gap-3 mb-6">
        {["all", "pending", "approved", "rejected"].map(
          (status) => (
            <button
              key={status}
              type="button"
              onClick={() => setFilter(status)}
              className={`px-4 py-2 rounded-lg font-bold capitalize ${
                filter === status
                  ? "bg-green-700 text-white"
                  : "bg-slate-100 text-slate-700 hover:bg-slate-200"
              }`}
            >
              {status}
            </button>
          )
        )}
      </div>

      {filteredRequests.length === 0 ? (
        <EmptyState
          title="No adoption requests found"
          text="Requests matching this status will appear here."
        />
      ) : (
        <div className="space-y-5">
          {filteredRequests.map((request) => (
            <AdoptionRequestCard
              key={request.id}
              request={request}
              onApprove={() =>
                onUpdate(request.id, "approved")
              }
              onReject={() =>
                onUpdate(request.id, "rejected")
              }
            />
          ))}
        </div>
      )}
    </Panel>
  );
}

function AnimalManagementCard({
  animal,
  onEdit,
  onDelete,
}) {
  return (
    <article className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm flex flex-col">
      <AnimalImage
        src={animal.image_url}
        alt={animal.name}
        type={animal.type}
      />

      <div className="p-5 flex flex-col flex-1">
        <div className="flex items-start justify-between gap-4 mb-3">
          <div>
            <h3 className="text-2xl font-extrabold text-green-800">
              {animal.name}
            </h3>

            <p className="text-slate-600 capitalize">
              {animal.type} • {animal.breed || "Mixed breed"}
            </p>
          </div>

          <StatusBadge status={animal.adoption_status} />
        </div>

        <div className="text-sm text-slate-600 space-y-1 mb-5">
          <p>
            <span className="font-bold">Age:</span>{" "}
            {animal.age || "Not provided"}
          </p>

          <p>
            <span className="font-bold">Gender:</span>{" "}
            {animal.gender || "Not provided"}
          </p>

          <p>
            <span className="font-bold">Location:</span>{" "}
            {animal.location || "Not provided"}
          </p>

          <p>
            <span className="font-bold">Health:</span>{" "}
            {animal.health_status || "Not provided"}
          </p>
        </div>

        <div className="mt-auto flex gap-3">
          <button
            type="button"
            onClick={() => onEdit(animal)}
            className="flex-1 bg-blue-600 text-white py-2.5 rounded-lg font-bold hover:bg-blue-700"
          >
            Edit
          </button>

          <button
            type="button"
            onClick={() => onDelete(animal.id)}
            className="flex-1 bg-red-600 text-white py-2.5 rounded-lg font-bold hover:bg-red-700"
          >
            Delete
          </button>
        </div>
      </div>
    </article>
  );
}

function AdoptionRequestCard({
  request,
  onApprove,
  onReject,
}) {
  const rawScore = Number(request.compatibility_score);

  const hasCompatibilityScore =
    request.compatibility_score !== null &&
    request.compatibility_score !== undefined &&
    !Number.isNaN(rawScore);

  const score = hasCompatibilityScore
    ? Math.max(0, Math.min(100, rawScore))
    : null;

  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="mb-1 text-sm font-bold text-slate-500">
            Adoption Application
          </p>

          <h3 className="text-2xl font-extrabold text-green-800">
            {request.user_name || "User"} wants to adopt{" "}
            {request.animal_name || "this animal"}
          </h3>

          <p className="mt-1 text-slate-600">
            {request.user_email || "Email not provided"}
          </p>

          {request.user_phone && (
            <p className="text-slate-600">
              {request.user_phone}
            </p>
          )}
        </div>

        <StatusBadge status={request.status} />
      </div>

      {hasCompatibilityScore && (
        <div className="mt-6 rounded-xl border border-green-200 bg-green-50 p-5">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-sm font-bold text-green-700">
                AI-Assisted Matching
              </p>

              <h4 className="font-extrabold text-green-900">
                Compatibility Score
              </h4>
            </div>

            <span className="text-3xl font-extrabold text-green-700">
              {score}%
            </span>
          </div>

          <div className="mt-3 h-3 overflow-hidden rounded-full bg-green-100">
            <div
              className="h-full rounded-full bg-green-700"
              style={{
                width: `${score}%`,
              }}
            />
          </div>
        </div>
      )}

      {request.ai_summary && (
        <div className="mt-5 rounded-xl border border-purple-200 bg-purple-50 p-5">
          <div className="mb-3 flex items-center gap-3">
            <span className="text-2xl">🤖</span>

            <div>
              <p className="text-sm font-bold text-purple-700">
                Decision Support
              </p>

              <h4 className="font-extrabold text-purple-900">
                AI Shelter Summary
              </h4>
            </div>
          </div>

          <p className="leading-7 text-slate-700">
            {request.ai_summary}
          </p>

          <p className="mt-3 text-xs text-purple-700">
            This summary supports shelter review. The final
            adoption decision belongs to the shelter.
          </p>
        </div>
      )}

      <div className="mt-5 rounded-xl border border-slate-200 bg-slate-50 p-5">
        <p className="mb-2 text-sm font-bold text-slate-500">
          Applicant Reason
        </p>

        <p className="leading-7 text-slate-700">
          {request.reason || "No message provided."}
        </p>
      </div>

      <p className="mt-5 text-sm text-slate-500">
        Submitted: {formatDate(request.created_at)}
      </p>

      {request.status?.toLowerCase() === "pending" && (
        <div className="mt-6 flex flex-wrap gap-3">
          <button
            type="button"
            onClick={onApprove}
            className="rounded-lg bg-green-700 px-6 py-3 font-bold text-white hover:bg-green-800"
          >
            Approve
          </button>

          <button
            type="button"
            onClick={onReject}
            className="rounded-lg bg-red-600 px-6 py-3 font-bold text-white hover:bg-red-700"
          >
            Reject
          </button>
        </div>
      )}
    </article>
  );
}


function SideItem({
  icon,
  label,
  tab,
  activeTab,
  setActiveTab,
  badge,
}) {
  return (
    <button
      type="button"
      onClick={() => setActiveTab(tab)}
      className={`w-full flex items-center justify-between gap-3 px-4 py-3 rounded-xl font-bold ${
        activeTab === tab
          ? "bg-green-700 text-white"
          : "text-slate-300 hover:bg-slate-900 hover:text-white"
      }`}
    >
      <span className="flex items-center gap-3">
        <span>{icon}</span>
        <span>{label}</span>
      </span>

      {badge > 0 && (
        <span className="bg-red-500 text-white text-xs min-w-6 h-6 px-2 rounded-full flex items-center justify-center">
          {badge}
        </span>
      )}
    </button>
  );
}

function StatCard({ label, value, icon, note }) {
  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-slate-500 font-semibold">
            {label}
          </p>

          <p className="text-4xl font-extrabold mt-2">
            {value}
          </p>

          <p className="text-sm text-slate-500 mt-2">
            {note}
          </p>
        </div>

        <div className="w-12 h-12 rounded-xl bg-green-100 text-green-800 flex items-center justify-center text-xl font-extrabold">
          {icon}
        </div>
      </div>
    </div>
  );
}

function Panel({ title, action, children }) {
  return (
    <section className="bg-white border border-slate-200 rounded-2xl shadow-sm p-6">
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
        <h2 className="text-2xl font-extrabold">
          {title}
        </h2>

        {action}
      </div>

      {children}
    </section>
  );
}

function FormSection({ title, description, children }) {
  return (
    <section className="border border-slate-200 rounded-2xl p-6">
      <h3 className="text-xl font-extrabold">{title}</h3>

      <p className="text-slate-500 mt-1 mb-5">
        {description}
      </p>

      {children}
    </section>
  );
}

function Input({
  label,
  name,
  value,
  onChange,
  placeholder,
  required,
}) {
  return (
    <div>
      <label className="block mb-2 font-bold">
        {label}

        {required && (
          <span className="text-red-600 ml-1">*</span>
        )}
      </label>

      <input
        type="text"
        name={name}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        required={required}
        className="w-full border border-slate-300 p-3 rounded-xl"
      />
    </div>
  );
}

function Select({
  label,
  name,
  value,
  onChange,
  children,
}) {
  return (
    <div>
      <label className="block mb-2 font-bold">
        {label}
      </label>

      <select
        name={name}
        value={value}
        onChange={onChange}
        className="w-full border border-slate-300 p-3 rounded-xl bg-white"
      >
        {children}
      </select>
    </div>
  );
}

function StatusBadge({ status }) {
  const normalizedStatus = status?.toLowerCase();

  const styles = {
    available: "bg-green-100 text-green-800",
    pending: "bg-orange-100 text-orange-800",
    adopted: "bg-purple-100 text-purple-800",
    approved: "bg-green-100 text-green-800",
    rejected: "bg-red-100 text-red-800",
  };

  return (
    <span
      className={`h-fit px-3 py-1 rounded-full text-sm font-bold capitalize ${
        styles[normalizedStatus] ||
        "bg-slate-100 text-slate-700"
      }`}
    >
      {status || "unknown"}
    </span>
  );
}

function AnimalImage({ src, alt, type }) {
  const [failed, setFailed] = useState(false);

  const emoji =
    type?.toLowerCase() === "cat" ? "🐱" : "🐶";

  if (!src || failed) {
    return (
      <div className="w-full h-52 bg-slate-200 flex items-center justify-center text-7xl">
        {emoji}
      </div>
    );
  }

  return (
    <img
      src={src}
      alt={alt}
      onError={() => setFailed(true)}
      className="w-full h-52 object-cover bg-slate-200"
    />
  );
}

function RecentAnimalItem({ animal }) {
  return (
    <div className="border border-slate-200 rounded-xl p-4 flex items-center justify-between gap-4">
      <div>
        <h3 className="font-extrabold text-green-800">
          {animal.name}
        </h3>

        <p className="text-sm text-slate-600 capitalize">
          {animal.type} • {animal.breed || "Mixed breed"} •{" "}
          {animal.location || "Location not provided"}
        </p>
      </div>

      <StatusBadge status={animal.adoption_status} />
    </div>
  );
}

function RecentRequestItem({ request }) {
  return (
    <div className="border border-slate-200 rounded-xl p-4 flex items-center justify-between gap-4">
      <div>
        <h3 className="font-extrabold text-green-800">
          {request.user_name || "User"}
        </h3>

        <p className="text-sm text-slate-600">
          Requested {request.animal_name || "an animal"}
        </p>
      </div>

      <StatusBadge status={request.status} />
    </div>
  );
}

function QuickAction({ title, text, icon, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="text-left border border-slate-200 rounded-xl p-5 hover:border-green-500 hover:bg-green-50"
    >
      <div className="text-2xl font-extrabold text-green-800 mb-3">
        {icon}
      </div>

      <h3 className="font-extrabold text-lg">
        {title}
      </h3>

      <p className="text-sm text-slate-600 mt-1">
        {text}
      </p>
    </button>
  );
}

function EmptyState({
  title,
  text,
  buttonText,
  onClick,
}) {
  return (
    <div className="text-center border border-dashed border-slate-300 rounded-xl p-8">
      <h3 className="text-xl font-extrabold">
        {title}
      </h3>

      <p className="text-slate-600 mt-2">
        {text}
      </p>

      {buttonText && onClick && (
        <button
          type="button"
          onClick={onClick}
          className="mt-5 bg-green-700 text-white px-5 py-2.5 rounded-lg font-bold"
        >
          {buttonText}
        </button>
      )}
    </div>
  );
}

function LoadingPanel() {
  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-10 text-center">
      <p className="font-semibold text-slate-600">
        Loading shelter dashboard...
      </p>
    </div>
  );
}

function getPageTitle(activeTab, editingAnimalId) {
  const titles = {
    dashboard: "Shelter Dashboard",
    animals: "Manage Animals",
    addAnimal: editingAnimalId
      ? "Edit Animal"
      : "Add New Animal",
    adoptionRequests: "Adoption Requests",
  };

  return titles[activeTab] || "Shelter Dashboard";
}

function getPageDescription(activeTab) {
  const descriptions = {
    dashboard:
      "Monitor animals and adoption activity from one place.",
    animals:
      "Search, edit, delete and update your animal records.",
    addAnimal:
      "Create a complete public profile for an adoptable animal.",
    adoptionRequests:
      "Review and manage adoption applications.",
  };

  return descriptions[activeTab] || "";
}

function formatDate(dateValue) {
  if (!dateValue) {
    return "Not available";
  }

  const date = new Date(dateValue);

  if (Number.isNaN(date.getTime())) {
    return dateValue;
  }

  return date.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

async function readJsonResponse(response) {
  const contentType = response.headers.get("content-type");

  if (!contentType?.includes("application/json")) {
    const text = await response.text();

    throw new Error(
      `The server returned an invalid response: ${text.slice(
        0,
        100
      )}`
    );
  }

  return response.json();
}